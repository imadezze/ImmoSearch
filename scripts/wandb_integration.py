#!/usr/bin/env python
"""
Weights & Biases (W&B) Weave integration for MCP Leboncoin tools.
Provides tracing, evaluation, and monitoring capabilities.
"""

import os
import weave
from typing import Dict, Any, Optional, List
from datetime import datetime
import json


class WeaveTracer:
    """W&B Weave integration for tracing MCP operations."""

    def __init__(self, project_name: str = "mcp-leboncoin", entity: Optional[str] = None):
        """
        Initialize Weave client for tracing.

        Args:
            project_name: W&B project name
            entity: W&B entity/team name (optional)
        """
        self.project_name = project_name
        self.entity = entity
        self.initialized = False

        # Check if WANDB_API_KEY is available before trying to initialize
        wandb_api_key = os.environ.get("WANDB_API_KEY")
        if not wandb_api_key:
            print("⚠️  WANDB_API_KEY not found. Tracing will be disabled.")
            return

        # Try to initialize Weave only if API key is available
        try:
            if entity:
                weave_project = f"{entity}/{project_name}"
            else:
                weave_project = project_name

            weave.init(weave_project)
            self.initialized = True
            print(f"✅ W&B Weave initialized for project: {weave_project}")
        except Exception as e:
            print(f"⚠️  W&B Weave initialization failed: {e}")
            print("Tracing will be disabled. Set WANDB_API_KEY to enable.")

    def is_enabled(self) -> bool:
        """Check if Weave tracing is enabled."""
        return self.initialized

    @weave.op()
    def trace_property_search(
        self,
        location: str,
        workplace: str,
        property_type: str,
        search_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Trace property search operations with rich metadata.

        Args:
            location: Search location
            workplace: Workplace for travel calculations
            property_type: "rental" or "sale"
            search_results: Results from the search

        Returns:
            Enhanced results with tracing metadata
        """
        # Add search metadata
        search_metadata = {
            "search_params": {
                "location": location,
                "workplace": workplace,
                "property_type": property_type,
                "timestamp": datetime.now().isoformat()
            },
            "results_summary": {
                "status": search_results.get("status"),
                "property_count": search_results.get("returned_count", 0),
                "total_available": search_results.get("search_summary", {}).get("total_results", 0)
            }
        }

        # Add tracing metadata to results
        enhanced_results = search_results.copy()
        enhanced_results["weave_metadata"] = search_metadata

        return enhanced_results

    @weave.op()
    def trace_travel_calculation(
        self,
        origin_coords: tuple,
        destination: str,
        mode: str,
        travel_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Trace travel time calculations.

        Args:
            origin_coords: (lat, lng) coordinates
            destination: Destination address
            mode: Travel mode (transit, driving, etc.)
            travel_result: Travel calculation results

        Returns:
            Travel results with tracing metadata
        """
        travel_metadata = {
            "calculation_params": {
                "origin_lat": origin_coords[0],
                "origin_lng": origin_coords[1],
                "destination": destination,
                "mode": mode,
                "timestamp": datetime.now().isoformat()
            },
            "calculation_results": {
                "distance_km": travel_result.get("distance_m", 0) / 1000.0,
                "duration_min": travel_result.get("duration_min", 0),
                "status": travel_result.get("status", "unknown")
            }
        }

        enhanced_result = travel_result.copy()
        enhanced_result["weave_metadata"] = travel_metadata

        return enhanced_result

    @weave.op()
    def trace_city_review_scraping(
        self,
        city_name: str,
        scraping_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Trace city review scraping operations.

        Args:
            city_name: Name of the city
            scraping_result: Results from scraping

        Returns:
            Scraping results with tracing metadata
        """
        scraping_metadata = {
            "scraping_params": {
                "city_name": city_name,
                "timestamp": datetime.now().isoformat()
            },
            "scraping_results": {
                "status": scraping_result.get("status"),
                "reviews_count": len(scraping_result.get("reviews", [])),
                "ratings_available": bool(scraping_result.get("ratings")),
                "url": scraping_result.get("url")
            }
        }

        enhanced_result = scraping_result.copy()
        enhanced_result["weave_metadata"] = scraping_metadata

        return enhanced_result

    def log_feedback(self, trace_id: str, feedback_type: str, feedback_data: Any):
        """
        Log user feedback to a trace.

        Args:
            trace_id: Weave trace ID
            feedback_type: Type of feedback ("reaction", "comment", "annotation")
            feedback_data: Feedback content
        """
        if not self.initialized:
            return

        try:
            # This would be implemented with Weave's feedback API
            # For now, we'll print the feedback
            print(f"📝 W&B Feedback [{feedback_type}] for trace {trace_id}: {feedback_data}")
        except Exception as e:
            print(f"❌ Failed to log feedback: {e}")


# Global tracer instance
_tracer: Optional[WeaveTracer] = None


def initialize_weave(project_name: str = "mcp-leboncoin", entity: Optional[str] = None) -> WeaveTracer:
    """
    Initialize the global Weave tracer.

    Args:
        project_name: W&B project name
        entity: W&B entity/team name

    Returns:
        WeaveTracer instance
    """
    global _tracer
    _tracer = WeaveTracer(project_name, entity)
    return _tracer


def get_tracer() -> Optional[WeaveTracer]:
    """Get the global tracer instance."""
    return _tracer


def ensure_tracer() -> WeaveTracer:
    """Ensure tracer is initialized and return it."""
    global _tracer
    if _tracer is None:
        _tracer = initialize_weave()
    return _tracer


# Decorator for automatic tracing
def trace_mcp_operation(operation_name: str):
    """
    Decorator to automatically trace MCP operations.

    Args:
        operation_name: Name of the operation for tracing
    """
    def decorator(func):
        if get_tracer() and get_tracer().is_enabled():
            return weave.op(name=operation_name)(func)
        else:
            # Return original function if tracing is disabled
            return func
    return decorator


# Context manager for operation tracking
class WeaveOperationContext:
    """Context manager for tracking operations in W&B Weave."""

    def __init__(self, operation_name: str, **kwargs):
        self.operation_name = operation_name
        self.params = kwargs
        self.tracer = get_tracer()

    def __enter__(self):
        if self.tracer and self.tracer.is_enabled():
            print(f"🔍 W&B Weave: Starting operation '{self.operation_name}'")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.tracer and self.tracer.is_enabled():
            status = "error" if exc_type else "success"
            print(f"✅ W&B Weave: Completed operation '{self.operation_name}' with status: {status}")