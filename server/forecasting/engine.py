"""
Time-series forecasting engine with multiple methods.
Implements Holt-Winters, exponential smoothing, and trend detection.
"""
import math
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from server.lib.lazy_imports import np, scipy_stats

from .models import (
    ForecastConfig,
    ForecastResult,
    ForecastPoint,
    TrendAnalysis,
    ForecastMethod,
    SeasonalityType,
)


def create_forecast(
    historical_values: List[float],
    metric_name: str,
    config: Optional[ForecastConfig] = None,
    start_date: Optional[datetime] = None,
) -> ForecastResult:
    """
    Create a forecast for a time series.
    
    Args:
        historical_values: List of historical values (monthly data points)
        metric_name: Name of the metric being forecast
        config: Forecast configuration
        start_date: Start date of historical data
        
    Returns:
        ForecastResult with predictions and analysis
    """
    if config is None:
        config = ForecastConfig()
    
    if start_date is None:
        start_date = datetime.utcnow() - timedelta(days=30 * len(historical_values))
    
    values = np.array(historical_values, dtype=float)
    n = len(values)
    
    if n < 3:
        raise ValueError("Need at least 3 data points for forecasting")
    
    # Choose method based on data and config
    if config.method == ForecastMethod.LINEAR:
        forecast_values, trend_comp, seasonal_comp = _linear_forecast(values, config)
    elif config.method == ForecastMethod.EXPONENTIAL:
        forecast_values, trend_comp, seasonal_comp = _exponential_smoothing(values, config)
    elif config.method == ForecastMethod.HOLT_WINTERS:
        forecast_values, trend_comp, seasonal_comp = _holt_winters(values, config)
    else:
        forecast_values, trend_comp, seasonal_comp = _holt_winters(values, config)
    
    # Calculate confidence intervals
    residuals = _calculate_residuals(values, trend_comp[:n], seasonal_comp[:n])
    std_error = np.std(residuals) if len(residuals) > 1 else 0.1 * np.mean(values)
    z_score = scipy_stats.norm.ppf((1 + config.confidence_level) / 2)
    
    # Build historical points
    historical_points = []
    for i in range(n):
        month_date = start_date + timedelta(days=30 * i)
        historical_points.append(ForecastPoint(
            month=i + 1,
            date=month_date,
            value=values[i],
            lower_bound=values[i],
            upper_bound=values[i],
            trend=trend_comp[i],
            seasonal=seasonal_comp[i] if i < len(seasonal_comp) else 0,
            residual=residuals[i] if i < len(residuals) else 0,
        ))
    
    # Build forecast points
    forecast_points = []
    for i in range(config.horizon_months):
        idx = n + i
        month_date = start_date + timedelta(days=30 * idx)
        value = forecast_values[i]
        
        # Widen confidence interval further into future
        interval_width = z_score * std_error * math.sqrt(1 + i * 0.1)
        lower = max(config.floor, value - interval_width)
        upper = value + interval_width
        if config.growth_cap:
            upper = min(upper, config.growth_cap)
        
        forecast_points.append(ForecastPoint(
            month=idx + 1,
            date=month_date,
            value=value,
            lower_bound=lower,
            upper_bound=upper,
            trend=trend_comp[idx] if idx < len(trend_comp) else trend_comp[-1],
            seasonal=seasonal_comp[idx % len(seasonal_comp)] if len(seasonal_comp) > 0 else 0,
            residual=0,
        ))
    
    # Analyze trend
    trend_analysis = detect_trend(values)
    
    # Calculate accuracy metrics using holdout if enough data
    accuracy = _calculate_accuracy(values, trend_comp[:n] + seasonal_comp[:n])
    
    return ForecastResult(
        metric_name=metric_name,
        method=config.method,
        config=config,
        historical=historical_points,
        forecast=forecast_points,
        trend_analysis=trend_analysis,
        accuracy_metrics=accuracy,
    )


def forecast_revenue(
    monthly_revenue: List[float],
    horizon_months: int = 12,
    seasonality: SeasonalityType = SeasonalityType.MONTHLY,
) -> ForecastResult:
    """Convenience function for revenue forecasting."""
    config = ForecastConfig(
        method=ForecastMethod.HOLT_WINTERS,
        horizon_months=horizon_months,
        seasonality=seasonality,
        floor=0.0,
    )
    return create_forecast(monthly_revenue, "revenue", config)


def forecast_customers(
    monthly_customers: List[int],
    horizon_months: int = 12,
) -> ForecastResult:
    """Convenience function for customer count forecasting."""
    config = ForecastConfig(
        method=ForecastMethod.EXPONENTIAL,
        horizon_months=horizon_months,
        seasonality=SeasonalityType.NONE,
        floor=0.0,
    )
    values = [float(c) for c in monthly_customers]
    return create_forecast(values, "customers", config)


def detect_trend(values: List[float]) -> TrendAnalysis:
    """
    Analyze trend direction and strength.
    """
    if len(values) < 2:
        return TrendAnalysis(
            direction="flat",
            strength=0.0,
            growth_rate=0.0,
            acceleration=0.0,
        )
    
    arr = np.array(values)
    n = len(arr)
    
    # Linear regression for trend
    x = np.arange(n)
    slope, intercept, r_value, _, _ = scipy_stats.linregress(x, arr)
    
    # Determine direction
    if abs(slope) < 0.01 * np.mean(arr):
        direction = "flat"
    elif slope > 0:
        direction = "up"
    else:
        direction = "down"
    
    # Strength is R-squared
    strength = min(1.0, max(0.0, r_value ** 2))
    
    # Growth rate (average month-over-month)
    if len(arr) > 1 and arr[0] != 0:
        growth_rates = []
        for i in range(1, len(arr)):
            if arr[i-1] > 0:
                growth_rates.append((arr[i] - arr[i-1]) / arr[i-1])
        growth_rate = np.mean(growth_rates) if growth_rates else 0.0
    else:
        growth_rate = 0.0
    
    # Acceleration (change in growth rate)
    if len(values) >= 4:
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        g1 = (first_half[-1] - first_half[0]) / max(first_half[0], 1) if len(first_half) > 1 else 0
        g2 = (second_half[-1] - second_half[0]) / max(second_half[0], 1) if len(second_half) > 1 else 0
        acceleration = g2 - g1
    else:
        acceleration = 0.0
    
    # Find inflection points (where second derivative changes sign)
    inflection_points = []
    if len(arr) >= 5:
        second_derivative = np.diff(np.diff(arr))
        for i in range(1, len(second_derivative)):
            if second_derivative[i-1] * second_derivative[i] < 0:
                inflection_points.append(i + 1)
    
    return TrendAnalysis(
        direction=direction,
        strength=strength,
        growth_rate=growth_rate,
        acceleration=acceleration,
        inflection_points=inflection_points,
    )


def _linear_forecast(
    values: np.ndarray,
    config: ForecastConfig,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Simple linear regression forecast."""
    n = len(values)
    x = np.arange(n)
    slope, intercept, _, _, _ = scipy_stats.linregress(x, values)
    
    # Trend component
    trend = slope * np.arange(n + config.horizon_months) + intercept
    
    # No seasonality in linear
    seasonal = np.zeros(n + config.horizon_months)
    
    # Forecast
    forecast = trend[n:n + config.horizon_months]
    forecast = np.maximum(forecast, config.floor)
    
    return forecast, trend, seasonal


def _exponential_smoothing(
    values: np.ndarray,
    config: ForecastConfig,
    alpha: float = 0.3,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Simple exponential smoothing with trend."""
    n = len(values)
    total_len = n + config.horizon_months
    
    # Initialize
    level = np.zeros(total_len)
    level[0] = values[0]
    
    # Fit
    for t in range(1, n):
        level[t] = alpha * values[t] + (1 - alpha) * level[t-1]
    
    # Forecast (level stays constant)
    for t in range(n, total_len):
        level[t] = level[n-1]
    
    forecast = level[n:total_len]
    forecast = np.maximum(forecast, config.floor)
    
    return forecast, level, np.zeros(total_len)


def _holt_winters(
    values: np.ndarray,
    config: ForecastConfig,
    alpha: float = 0.3,
    beta: float = 0.1,
    gamma: float = 0.2,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Holt-Winters exponential smoothing with trend and seasonality.
    """
    n = len(values)
    total_len = n + config.horizon_months
    
    # Determine season length
    if config.seasonality == SeasonalityType.MONTHLY:
        m = 12
    elif config.seasonality == SeasonalityType.QUARTERLY:
        m = 4
    elif config.seasonality == SeasonalityType.WEEKLY:
        m = 52
    else:
        m = 1  # No seasonality
    
    # Initialize components
    level = np.zeros(total_len)
    trend = np.zeros(total_len)
    seasonal = np.zeros(max(total_len, m))
    
    # Initialize level and trend
    level[0] = values[0]
    if n > 1:
        trend[0] = values[1] - values[0]
    
    # Initialize seasonal factors (if enough data)
    if m > 1 and n >= m:
        for i in range(m):
            indices = list(range(i, n, m))
            if indices:
                avg = np.mean([values[j] for j in indices])
                overall_avg = np.mean(values)
                seasonal[i] = avg / overall_avg if overall_avg > 0 else 1.0
    else:
        seasonal[:] = 1.0
    
    # Fit the model
    for t in range(1, n):
        s_idx = t % m if m > 1 else 0
        prev_s_idx = (t - m) % m if m > 1 else 0
        
        # Update level
        if seasonal[prev_s_idx] > 0:
            level[t] = alpha * (values[t] / seasonal[prev_s_idx]) + (1 - alpha) * (level[t-1] + trend[t-1])
        else:
            level[t] = alpha * values[t] + (1 - alpha) * (level[t-1] + trend[t-1])
        
        # Update trend
        trend[t] = beta * (level[t] - level[t-1]) + (1 - beta) * trend[t-1]
        
        # Update seasonal
        if m > 1 and level[t] > 0:
            seasonal[s_idx] = gamma * (values[t] / level[t]) + (1 - gamma) * seasonal[prev_s_idx]
    
    # Forecast
    forecast_values = np.zeros(config.horizon_months)
    for h in range(config.horizon_months):
        t = n + h
        s_idx = t % m if m > 1 else 0
        
        # Extend level and trend
        level[t] = level[n-1] + trend[n-1] * (h + 1)
        trend[t] = trend[n-1]
        
        # Forecast value
        forecast_values[h] = (level[t]) * seasonal[s_idx]
        forecast_values[h] = max(forecast_values[h], config.floor)
        
        if config.growth_cap and forecast_values[h] > config.growth_cap:
            forecast_values[h] = config.growth_cap
    
    # Expand level/trend arrays for return
    full_trend = np.concatenate([trend[:n], trend[n-1] + trend[n-1] * np.arange(1, config.horizon_months + 1)])
    
    return forecast_values, level[:total_len], seasonal


def _calculate_residuals(
    actual: np.ndarray,
    trend: np.ndarray,
    seasonal: np.ndarray,
) -> np.ndarray:
    """Calculate residuals from trend and seasonal components."""
    n = len(actual)
    fitted = trend[:n] * (seasonal[:n] if len(seasonal) >= n else np.ones(n))
    return actual - fitted


def _calculate_accuracy(
    actual: np.ndarray,
    fitted: np.ndarray,
) -> dict:
    """Calculate forecast accuracy metrics."""
    n = len(actual)
    if n == 0:
        return {"mape": 0.0, "rmse": 0.0, "mae": 0.0}
    
    fitted = fitted[:n]
    errors = actual - fitted
    
    # RMSE
    rmse = np.sqrt(np.mean(errors ** 2))
    
    # MAE
    mae = np.mean(np.abs(errors))
    
    # MAPE (avoid division by zero)
    non_zero = actual != 0
    if np.any(non_zero):
        mape = np.mean(np.abs(errors[non_zero] / actual[non_zero])) * 100
    else:
        mape = 0.0
    
    return {
        "mape": float(mape),
        "rmse": float(rmse),
        "mae": float(mae),
    }
