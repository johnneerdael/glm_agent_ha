"""Performance monitoring system for GLM Agent HA integration."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from statistics import mean, median, stdev

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Individual request performance metrics."""
    timestamp: datetime
    request_id: str
    request_type: str
    provider: str
    model: Optional[str]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    duration_ms: float
    success: bool
    error_type: Optional[str]
    cache_hit: bool
    user_id: Optional[str]
    prompt_length: int
    response_length: int


@dataclass
class AggregatedMetrics:
    """Aggregated performance metrics over a time period."""
    period_start: datetime
    period_end: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_duration_ms: float
    median_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    total_input_tokens: int
    total_output_tokens: int
    cache_hit_rate: float
    error_rate: float
    requests_by_type: Dict[str, int]
    requests_by_provider: Dict[str, int]
    requests_by_model: Dict[str, int]
    top_errors: List[Dict[str, Any]]


class GLMAgentPerformanceMonitor:
    """Performance monitoring system for AI requests."""

    def __init__(self, hass: HomeAssistant, max_history: int = 10000):
        """Initialize the performance monitor.

        Args:
            hass: Home Assistant instance
            max_history: Maximum number of request records to keep in memory
        """
        self.hass = hass
        self.max_history = max_history

        # In-memory storage for recent requests
        self._request_history: deque[RequestMetrics] = deque(maxlen=max_history)
        self._request_cache: Dict[str, RequestMetrics] = {}

        # Real-time counters
        self._counters = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
        }

        # Aggregated metrics cache
        self._aggregated_cache: Dict[str, AggregatedMetrics] = {}
        self._last_aggregation = datetime.now()

        # Performance alerts
        self._alert_thresholds = {
            "duration_ms": 5000,  # Alert if request takes > 5 seconds
            "error_rate": 0.10,   # Alert if error rate > 10%
            "memory_usage_mb": 1000,  # Alert if memory usage > 1GB
        }

        _LOGGER.info("Performance monitor initialized with max_history=%d", max_history)

    def start_request(self, request_id: str, request_type: str, provider: str,
                     model: Optional[str] = None, user_id: Optional[str] = None,
                     prompt: Optional[str] = None) -> str:
        """Start monitoring a new request.

        Args:
            request_id: Unique identifier for the request
            request_type: Type of request (query, automation, dashboard, etc.)
            provider: AI provider (openai, etc.)
            model: AI model being used
            user_id: User making the request
            prompt: The prompt content (for length tracking)

        Returns:
            The request ID (for reference)
        """
        request_metrics = RequestMetrics(
            timestamp=datetime.now(),
            request_id=request_id,
            request_type=request_type,
            provider=provider,
            model=model,
            input_tokens=None,
            output_tokens=None,
            duration_ms=0.0,
            success=False,
            error_type=None,
            cache_hit=False,
            user_id=user_id,
            prompt_length=len(prompt) if prompt else 0,
            response_length=0,
        )

        self._request_cache[request_id] = request_metrics
        self._counters["total_requests"] += 1

        _LOGGER.debug("Started monitoring request %s: %s via %s",
                     request_id, request_type, provider)

        return request_id

    def end_request(self, request_id: str, success: bool = True,
                   error_type: Optional[str] = None,
                   input_tokens: Optional[int] = None,
                   output_tokens: Optional[int] = None,
                   response: Optional[str] = None,
                   cache_hit: bool = False) -> Optional[RequestMetrics]:
        """End monitoring for a request and record metrics.

        Args:
            request_id: Unique identifier for the request
            success: Whether the request was successful
            error_type: Type of error if request failed
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
            response: The response content (for length tracking)
            cache_hit: Whether the result was served from cache

        Returns:
            The completed request metrics, or None if request_id not found
        """
        if request_id not in self._request_cache:
            _LOGGER.warning("Attempted to end unknown request: %s", request_id)
            return None

        request_metrics = self._request_cache.pop(request_id)

        # Calculate duration
        end_time = datetime.now()
        duration_ms = (end_time - request_metrics.timestamp).total_seconds() * 1000

        # Update metrics
        request_metrics.duration_ms = duration_ms
        request_metrics.success = success
        request_metrics.error_type = error_type
        request_metrics.input_tokens = input_tokens
        request_metrics.output_tokens = output_tokens
        request_metrics.cache_hit = cache_hit
        request_metrics.response_length = len(response) if response else 0

        # Update counters
        if success:
            self._counters["successful_requests"] += 1
        else:
            self._counters["failed_requests"] += 1

        if cache_hit:
            self._counters["cache_hits"] += 1

        if input_tokens:
            self._counters["total_input_tokens"] += input_tokens

        if output_tokens:
            self._counters["total_output_tokens"] += output_tokens

        # Store in history
        self._request_history.append(request_metrics)

        # Check for performance alerts
        self._check_performance_alerts(request_metrics)

        _LOGGER.debug("Completed request %s: %.2fms, success=%s, tokens=%d/%d",
                     request_id, duration_ms, success, input_tokens or 0, output_tokens or 0)

        return request_metrics

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current real-time performance metrics.

        Returns:
            Dictionary containing current performance statistics
        """
        if not self._request_history:
            return {
                "timestamp": datetime.now().isoformat(),
                "total_requests": 0,
                "requests_per_minute": 0,
                "success_rate": 0.0,
                "average_duration_ms": 0.0,
                "cache_hit_rate": 0.0,
                "current_session": True
            }

        # Calculate recent metrics (last 5 minutes)
        now = datetime.now()
        five_minutes_ago = now - timedelta(minutes=5)
        recent_requests = [
            r for r in self._request_history
            if r.timestamp >= five_minutes_ago
        ]

        # Calculate rates
        requests_per_minute = len(recent_requests) / 5.0 if recent_requests else 0

        # Calculate success rate
        successful_count = sum(1 for r in recent_requests if r.success)
        success_rate = (successful_count / len(recent_requests)) if recent_requests else 0

        # Calculate average duration
        durations = [r.duration_ms for r in recent_requests]
        avg_duration = mean(durations) if durations else 0

        # Calculate cache hit rate
        cache_hits = sum(1 for r in recent_requests if r.cache_hit)
        cache_hit_rate = (cache_hits / len(recent_requests)) if recent_requests else 0

        # Get current active requests
        active_requests = len(self._request_cache)

        return {
            "timestamp": now.isoformat(),
            "total_requests": self._counters["total_requests"],
            "active_requests": active_requests,
            "requests_per_minute": requests_per_minute,
            "success_rate": round(success_rate * 100, 2),
            "average_duration_ms": round(avg_duration, 2),
            "cache_hit_rate": round(cache_hit_rate * 100, 2),
            "total_input_tokens": self._counters["total_input_tokens"],
            "total_output_tokens": self._counters["total_output_tokens"],
            "current_session": True,
            "memory_usage_mb": self._estimate_memory_usage()
        }

    def get_aggregated_metrics(self, period_hours: int = 24) -> AggregatedMetrics:
        """Get aggregated metrics for a time period.

        Args:
            period_hours: Number of hours to aggregate over

        Returns:
            AggregatedMetrics object with performance statistics
        """
        cache_key = f"aggregated_{period_hours}h"

        # Check cache first (refresh every 5 minutes)
        if (cache_key in self._aggregated_cache and
            (datetime.now() - self._last_aggregation).total_seconds() < 300):
            return self._aggregated_cache[cache_key]

        # Calculate period bounds
        now = datetime.now()
        period_start = now - timedelta(hours=period_hours)

        # Filter requests in period
        period_requests = [
            r for r in self._request_history
            if r.timestamp >= period_start
        ]

        if not period_requests:
            # Return empty metrics
            metrics = AggregatedMetrics(
                period_start=period_start,
                period_end=now,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                average_duration_ms=0.0,
                median_duration_ms=0.0,
                p95_duration_ms=0.0,
                p99_duration_ms=0.0,
                min_duration_ms=0.0,
                max_duration_ms=0.0,
                total_input_tokens=0,
                total_output_tokens=0,
                cache_hit_rate=0.0,
                error_rate=0.0,
                requests_by_type={},
                requests_by_provider={},
                requests_by_model={},
                top_errors=[]
            )
            self._aggregated_cache[cache_key] = metrics
            return metrics

        # Calculate basic statistics
        total_requests = len(period_requests)
        successful_requests = sum(1 for r in period_requests if r.success)
        failed_requests = total_requests - successful_requests

        # Duration statistics
        durations = [r.duration_ms for r in period_requests]
        durations.sort()

        average_duration = mean(durations)
        median_duration = median(durations)
        p95_duration = durations[int(len(durations) * 0.95)] if len(durations) > 20 else max(durations)
        p99_duration = durations[int(len(durations) * 0.99)] if len(durations) > 100 else max(durations)
        min_duration = min(durations)
        max_duration = max(durations)

        # Token statistics
        total_input_tokens = sum(r.input_tokens or 0 for r in period_requests)
        total_output_tokens = sum(r.output_tokens or 0 for r in period_requests)

        # Cache and error rates
        cache_hits = sum(1 for r in period_requests if r.cache_hit)
        cache_hit_rate = (cache_hits / total_requests) if total_requests > 0 else 0
        error_rate = (failed_requests / total_requests) if total_requests > 0 else 0

        # Request categorization
        requests_by_type = defaultdict(int)
        requests_by_provider = defaultdict(int)
        requests_by_model = defaultdict(int)

        for r in period_requests:
            requests_by_type[r.request_type] += 1
            requests_by_provider[r.provider] += 1
            if r.model:
                requests_by_model[r.model] += 1

        # Top errors
        error_counts = defaultdict(int)
        for r in period_requests:
            if r.error_type:
                error_counts[r.error_type] += 1

        top_errors = [
            {"error_type": error, "count": count}
            for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        # Create aggregated metrics
        metrics = AggregatedMetrics(
            period_start=period_start,
            period_end=now,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            average_duration_ms=round(average_duration, 2),
            median_duration_ms=round(median_duration, 2),
            p95_duration_ms=round(p95_duration, 2),
            p99_duration_ms=round(p99_duration, 2),
            min_duration_ms=round(min_duration, 2),
            max_duration_ms=round(max_duration, 2),
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            cache_hit_rate=round(cache_hit_rate * 100, 2),
            error_rate=round(error_rate * 100, 2),
            requests_by_type=dict(requests_by_type),
            requests_by_provider=dict(requests_by_provider),
            requests_by_model=dict(requests_by_model),
            top_errors=top_errors
        )

        # Cache the result
        self._aggregated_cache[cache_key] = metrics
        self._last_aggregation = now

        return metrics

    def get_performance_trends(self, days: int = 7) -> Dict[str, Any]:
        """Get performance trends over multiple days.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary containing trend data
        """
        now = datetime.now()
        trends = []

        for day_offset in range(days):
            day_start = (now - timedelta(days=day_offset)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            day_requests = [
                r for r in self._request_history
                if day_start <= r.timestamp < day_end
            ]

            if day_requests:
                total_requests = len(day_requests)
                successful_requests = sum(1 for r in day_requests if r.success)
                avg_duration = mean(r.duration_ms for r in day_requests)
                cache_hits = sum(1 for r in day_requests if r.cache_hit)
                cache_hit_rate = (cache_hits / total_requests) if total_requests > 0 else 0

                trends.append({
                    "date": day_start.strftime("%Y-%m-%d"),
                    "total_requests": total_requests,
                    "success_rate": round((successful_requests / total_requests) * 100, 2),
                    "average_duration_ms": round(avg_duration, 2),
                    "cache_hit_rate": round(cache_hit_rate * 100, 2)
                })
            else:
                trends.append({
                    "date": day_start.strftime("%Y-%m-%d"),
                    "total_requests": 0,
                    "success_rate": 0,
                    "average_duration_ms": 0,
                    "cache_hit_rate": 0
                })

        # Calculate trends (comparing recent days to older days)
        if len(trends) >= 2:
            recent_avg = mean(t["total_requests"] for t in trends[:3])
            older_avg = mean(t["total_requests"] for t in trends[3:7]) if len(trends) > 3 else recent_avg

            request_trend = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0

            recent_success_rate = mean(t["success_rate"] for t in trends[:3])
            older_success_rate = mean(t["success_rate"] for t in trends[3:7]) if len(trends) > 3 else recent_success_rate

            success_trend = recent_success_rate - older_success_rate
        else:
            request_trend = 0
            success_trend = 0

        return {
            "period_days": days,
            "daily_data": list(reversed(trends)),  # Most recent first
            "request_volume_trend_percent": round(request_trend, 2),
            "success_rate_trend_percent": round(success_trend, 2),
            "analysis_date": now.isoformat()
        }

    def get_top_slow_requests(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the slowest recent requests.

        Args:
            limit: Maximum number of requests to return

        Returns:
            List of slow request details
        """
        # Get requests from last 24 hours
        day_ago = datetime.now() - timedelta(days=1)
        recent_requests = [
            r for r in self._request_history
            if r.timestamp >= day_ago
        ]

        # Sort by duration (slowest first)
        slow_requests = sorted(recent_requests, key=lambda r: r.duration_ms, reverse=True)

        return [
            {
                "timestamp": r.timestamp.isoformat(),
                "request_id": r.request_id,
                "request_type": r.request_type,
                "provider": r.provider,
                "model": r.model,
                "duration_ms": round(r.duration_ms, 2),
                "success": r.success,
                "error_type": r.error_type,
                "prompt_length": r.prompt_length,
                "response_length": r.response_length,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens
            }
            for r in slow_requests[:limit]
        ]

    def _check_performance_alerts(self, request: RequestMetrics) -> None:
        """Check for performance issues and generate alerts.

        Args:
            request: The completed request to check
        """
        alerts = []

        # Check for slow requests
        if request.duration_ms > self._alert_thresholds["duration_ms"]:
            alerts.append({
                "type": "slow_request",
                "severity": "warning",
                "message": f"Slow {request.request_type} request: {request.duration_ms:.2f}ms",
                "request_id": request.request_id,
                "threshold_ms": self._alert_thresholds["duration_ms"]
            })

        # Check for memory usage (simplified estimate)
        memory_usage_mb = self._estimate_memory_usage()
        if memory_usage_mb > self._alert_thresholds["memory_usage_mb"]:
            alerts.append({
                "type": "high_memory_usage",
                "severity": "warning",
                "message": f"High memory usage: {memory_usage_mb:.2f}MB",
                "usage_mb": memory_usage_mb,
                "threshold_mb": self._alert_thresholds["memory_usage_mb"]
            })

        # Fire alerts via Home Assistant event bus
        for alert in alerts:
            self.hass.bus.async_fire("glm_agent_ha_performance_alert", alert)
            _LOGGER.warning("Performance alert: %s", alert["message"])

    def _estimate_memory_usage(self) -> float:
        """Estimate current memory usage in MB.

        Returns:
            Estimated memory usage in megabytes
        """
        try:
            import sys
            import gc

            # Rough estimate of object sizes
            total_objects = len(gc.get_objects())
            # Assume average object size of ~1KB (very rough estimate)
            estimated_bytes = total_objects * 1024
            estimated_mb = estimated_bytes / (1024 * 1024)

            return round(estimated_mb, 2)
        except Exception:
            return 0.0

    def reset_metrics(self) -> None:
        """Reset all performance metrics."""
        self._request_history.clear()
        self._request_cache.clear()
        self._counters = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
        }
        self._aggregated_cache.clear()
        self._last_aggregation = datetime.now()

        _LOGGER.info("Performance metrics reset")

    def export_metrics(self, format: str = "json") -> str:
        """Export performance metrics for external analysis.

        Args:
            format: Export format ("json" or "csv")

        Returns:
            Formatted metrics data
        """
        current_metrics = self.get_current_metrics()
        aggregated_24h = self.get_aggregated_metrics(24)
        trends_7d = self.get_performance_trends(7)
        slow_requests = self.get_top_slow_requests(5)

        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "monitor_version": "1.0.0",
            "current_metrics": current_metrics,
            "aggregated_24h": asdict(aggregated_24h),
            "trends_7d": trends_7d,
            "slow_requests": slow_requests
        }

        if format.lower() == "json":
            return json.dumps(export_data, indent=2, default=str)
        elif format.lower() == "csv":
            # Simple CSV export for requests
            csv_lines = ["timestamp,request_id,request_type,provider,model,duration_ms,success,error_type,input_tokens,output_tokens"]
            for request in list(self._request_history)[-1000:]:  # Last 1000 requests
                csv_lines.append(
                    f"{request.timestamp.isoformat()},"
                    f"{request.request_id},"
                    f"{request.request_type},"
                    f"{request.provider},"
                    f"{request.model or ''},"
                    f"{request.duration_ms},"
                    f"{request.success},"
                    f"{request.error_type or ''},"
                    f"{request.input_tokens or ''},"
                    f"{request.output_tokens or ''}"
                )
            return "\n".join(csv_lines)
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Decorator for automatic request monitoring
def monitor_performance(request_type: str, provider: str = "openai"):
    """Decorator to automatically monitor function performance.

    Args:
        request_type: Type of request being monitored
        provider: AI provider being used
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            # Extract hass instance and config from args
            hass = None
            config = None

            for arg in args:
                if isinstance(arg, HomeAssistant):
                    hass = arg
                elif isinstance(arg, dict) and "ai_provider" in arg:
                    config = arg

            # Try to get the domain from the function's module or default to "glm_agent_ha"
            domain = "glm_agent_ha"

            if not hass or not hasattr(hass.data.get(domain, {}), "performance_monitor"):
                # No monitoring available, just run the function
                return await func(*args, **kwargs)

            monitor = hass.data[domain].get("performance_monitor")
            if not monitor:
                return await func(*args, **kwargs)

            # Generate request ID
            request_id = f"{request_type}_{int(time.time() * 1000)}"

            # Extract additional parameters
            model = kwargs.get("model", config.get("model") if config else None)
            user_id = kwargs.get("user_id")
            prompt = kwargs.get("prompt", "")

            # Start monitoring
            monitor.start_request(request_id, request_type, provider, model, user_id, prompt)

            try:
                # Execute the function
                result = await func(*args, **kwargs)

                # Extract performance metrics from result if available
                success = True
                error_type = None
                input_tokens = None
                output_tokens = None
                response = None
                cache_hit = False

                if isinstance(result, dict):
                    input_tokens = result.get("usage", {}).get("prompt_tokens")
                    output_tokens = result.get("usage", {}).get("completion_tokens")
                    response = result.get("response", "")
                    cache_hit = result.get("cache_hit", False)
                elif isinstance(result, str):
                    response = result

                # End monitoring with success
                monitor.end_request(
                    request_id=request_id,
                    success=success,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    response=response,
                    cache_hit=cache_hit
                )

                return result

            except Exception as e:
                # End monitoring with error
                monitor.end_request(
                    request_id=request_id,
                    success=False,
                    error_type=type(e).__name__
                )
                raise

        return async_wrapper
    return decorator


# Performance monitoring context manager
class PerformanceMonitorContext:
    """Context manager for manual performance monitoring."""

    def __init__(self, monitor: GLMAgentPerformanceMonitor,
                 request_type: str, provider: str,
                 request_id: Optional[str] = None,
                 model: Optional[str] = None,
                 user_id: Optional[str] = None,
                 prompt: Optional[str] = None):
        """Initialize the context manager.

        Args:
            monitor: Performance monitor instance
            request_type: Type of request
            provider: AI provider
            request_id: Optional custom request ID
            model: AI model being used
            user_id: User making the request
            prompt: Request prompt
        """
        self.monitor = monitor
        self.request_type = request_type
        self.provider = provider
        self.request_id = request_id or f"{request_type}_{int(time.time() * 1000)}"
        self.model = model
        self.user_id = user_id
        self.prompt = prompt
        self.success = True
        self.error_type = None

    def __enter__(self):
        """Start monitoring when entering context."""
        self.monitor.start_request(
            self.request_id,
            self.request_type,
            self.provider,
            self.model,
            self.user_id,
            self.prompt
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End monitoring when exiting context."""
        if exc_type is not None:
            self.success = False
            self.error_type = exc_type.__name__

        self.monitor.end_request(
            request_id=self.request_id,
            success=self.success,
            error_type=self.error_type
        )

        # Don't suppress exceptions
        return False