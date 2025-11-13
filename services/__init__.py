"""
Services Layer - MEC Previsioni
Contiene la business logic separata dalle routes
"""

from .statistical_service import (
    weibull_logpost,
    fit_weibull_and_score,
    best_prior_weibull,
    compute_riskset,
    weibull_confidence_bands
)

from .prediction_service import (
    precompute_all_predictions,
    precompute_all_predictions_by_stat
)

from .chart_service import save_chart

from .data_service import (
    load_data_cache,
    get_historical_stats,
    generate_reliability_summary
)

__all__ = [
    # Statistical functions
    'weibull_logpost',
    'fit_weibull_and_score',
    'best_prior_weibull',
    'compute_riskset',
    'weibull_confidence_bands',

    # Prediction functions
    'precompute_all_predictions',
    'precompute_all_predictions_by_stat',

    # Chart functions
    'save_chart',

    # Data functions
    'load_data_cache',
    'get_historical_stats',
    'generate_reliability_summary'
]
