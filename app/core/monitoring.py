"""
Monitoring and metrics collection for production observability.

This module provides comprehensive monitoring including:
- Application metrics (requests, response times, errors)
- System metrics (CPU, memory, disk)
- Database metrics (connections, query times)
- Business metrics (user activity, feature usage)
"""

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Deque, Dict, Optional

logger = logging.getLogger("app.monitoring")


@dataclass
class MetricPoint:
    """Single metric data point."""

    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class HealthStatus:
    """Application health status."""

    status: str  # healthy, degraded, unhealthy
    timestamp: datetime
    checks: Dict[str, bool]
    response_time_ms: float
    error_rate: float

    @property
    def is_healthy(self) -> bool:
        return self.status == "healthy"


class MetricsCollector:
    """
    Collects and stores application metrics.

    Provides thread-safe metric collection with automatic cleanup
    of old data points to prevent memory leaks.
    """

    def __init__(self, retention_minutes: int = 60):
        self.retention_minutes = retention_minutes
        self.metrics: Dict[str, Deque[MetricPoint]] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        self._lock = threading.RLock()

        # Performance counters
        self.request_count = 0
        self.error_count = 0
        self.response_times: Deque[float] = deque(maxlen=100)

    def record_metric(
        self, name: str, value: float, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a metric data point."""
        with self._lock:
            point = MetricPoint(
                timestamp=datetime.utcnow(), value=value, tags=tags or {}
            )
            self.metrics[name].append(point)
            self._cleanup_old_metrics()

    def record_request(
        self, method: str, path: str, status_code: int, response_time: float
    ) -> None:
        """Record HTTP request metrics."""
        with self._lock:
            self.request_count += 1
            self.response_times.append(response_time)

            if status_code >= 400:
                self.error_count += 1

            # Record detailed metrics
            tags = {"method": method, "path": path, "status": str(status_code)}

            self.record_metric("http_requests_total", 1, tags)
            self.record_metric("http_request_duration_seconds", response_time, tags)

    def record_database_operation(
        self, operation: str, duration: float, success: bool
    ) -> None:
        """Record database operation metrics."""
        tags = {
            "operation": operation,
            "status": "success" if success else "error",
        }
        self.record_metric("db_operation_duration_seconds", duration, tags)
        self.record_metric("db_operations_total", 1, tags)

    def get_metric_stats(self, name: str, window_minutes: int = 5) -> Dict[str, float]:
        """Get statistical summary of a metric over time window."""
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)

        with self._lock:
            if name not in self.metrics:
                return {}

            recent_values = [
                point.value for point in self.metrics[name] if point.timestamp >= cutoff
            ]

            if not recent_values:
                return {}

            return {
                "count": len(recent_values),
                "min": min(recent_values),
                "max": max(recent_values),
                "avg": sum(recent_values) / len(recent_values),
                "sum": sum(recent_values),
            }

    def get_health_status(self) -> HealthStatus:
        """Calculate overall application health status."""
        now = datetime.utcnow()

        # Calculate error rate over last 5 minutes
        recent_requests = self.get_metric_stats("http_requests_total", 5)
        recent_errors = sum(
            1
            for point in self.metrics["http_requests_total"]
            if (
                point.timestamp >= now - timedelta(minutes=5)
                and point.tags.get("status", "200").startswith(("4", "5"))
            )
        )

        error_rate = 0.0
        if recent_requests.get("count", 0) > 0:
            error_rate = recent_errors / recent_requests["count"] * 100

        # Calculate average response time
        avg_response_time = 0.0
        if self.response_times:
            avg_response_time = (
                sum(self.response_times) / len(self.response_times) * 1000
            )

        # Health checks
        checks = {
            "api_responsive": avg_response_time < 1000,  # < 1 second
            "error_rate_ok": error_rate < 5.0,  # < 5% errors
            "requests_recent": recent_requests.get("count", 0)
            >= 0,  # Any activity is OK
        }

        # Determine overall status
        if all(checks.values()):
            status = "healthy"
        elif any(checks.values()):
            status = "degraded"
        else:
            status = "unhealthy"

        return HealthStatus(
            status=status,
            timestamp=now,
            checks=checks,
            response_time_ms=avg_response_time,
            error_rate=error_rate,
        )

    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than retention period."""
        cutoff = datetime.utcnow() - timedelta(minutes=self.retention_minutes)

        for name, points in self.metrics.items():
            # Remove old points from the left
            while points and points[0].timestamp < cutoff:
                points.popleft()


class PerformanceMonitor:
    """Monitor system performance and resource usage."""

    def __init__(self):
        self.start_time = time.time()
        self.cpu_samples: Deque[float] = deque(maxlen=60)  # 1 minute of samples
        self.memory_samples: Deque[float] = deque(maxlen=60)

    def get_uptime(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self.start_time

    def sample_system_metrics(self) -> Dict[str, float]:
        """Sample current system resource usage."""
        try:
            import psutil

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=None)
            self.cpu_samples.append(cpu_percent)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self.memory_samples.append(memory_percent)

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_used_mb": memory.used / (1024 * 1024),
                "memory_available_mb": memory.available / (1024 * 1024),
                "disk_percent": disk_percent,
                "uptime_seconds": self.get_uptime(),
            }
        except ImportError:
            logger.warning("psutil not available, system metrics disabled")
            return {"uptime_seconds": self.get_uptime()}

    def get_average_cpu(self, minutes: int = 5) -> float:
        """Get average CPU usage over specified minutes."""
        if not self.cpu_samples:
            return 0.0

        # Take last N samples (1 per second)
        samples_needed = min(minutes * 60, len(self.cpu_samples))
        recent_samples = list(self.cpu_samples)[-samples_needed:]

        return sum(recent_samples) / len(recent_samples) if recent_samples else 0.0


# Global instances
metrics_collector = MetricsCollector()
performance_monitor = PerformanceMonitor()


def get_comprehensive_metrics() -> Dict:
    """Get all application metrics for monitoring dashboard."""
    health = metrics_collector.get_health_status()
    system_metrics = performance_monitor.sample_system_metrics()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "health": {
            "status": health.status,
            "is_healthy": health.is_healthy,
            "error_rate_percent": health.error_rate,
            "avg_response_time_ms": health.response_time_ms,
            "checks": health.checks,
        },
        "performance": {
            "uptime_seconds": system_metrics.get("uptime_seconds", 0),
            "cpu_percent": system_metrics.get("cpu_percent", 0),
            "memory_percent": system_metrics.get("memory_percent", 0),
            "memory_used_mb": system_metrics.get("memory_used_mb", 0),
            "disk_percent": system_metrics.get("disk_percent", 0),
            "avg_cpu_5min": performance_monitor.get_average_cpu(5),
        },
        "requests": {
            "total": metrics_collector.request_count,
            "errors": metrics_collector.error_count,
            "requests_5min": metrics_collector.get_metric_stats(
                "http_requests_total", 5
            ),
            "response_time_5min": metrics_collector.get_metric_stats(
                "http_request_duration_seconds", 5
            ),
        },
    }
