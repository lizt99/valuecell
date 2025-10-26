"""Technical analysis of TradingView indicators"""

import logging
from typing import Dict, List, Any

from .constants import RSI_OVERBOUGHT, RSI_OVERSOLD
from .models import (
    CryptoTechnicalIndicators,
    MACDIndicator,
    OperationType,
    PositionSide,
    RSIIndicator,
    TimeSeriesIndicatorData,
)

logger = logging.getLogger(__name__)


class TradingViewTechnicalAnalyzer:
    """
    Technical analyzer for TradingView indicators
    Analyzes MACD, RSI, Chart Prime and other indicators
    """
    
    @staticmethod
    def analyze_macd(
        current: MACDIndicator,
        historical: List[MACDIndicator]
    ) -> Dict[str, Any]:
        """Analyze MACD indicator"""
        analysis = {
            "trend": "neutral",
            "signal_strength": 0,
            "key_observations": []
        }
        
        # Current state
        if current.is_bullish_crossover:
            analysis["trend"] = "bullish"
            analysis["signal_strength"] = 70
            analysis["key_observations"].append("MACD bullish crossover")
        elif current.is_bearish_crossover:
            analysis["trend"] = "bearish"
            analysis["signal_strength"] = -70
            analysis["key_observations"].append("MACD bearish crossover")
        elif current.macd_line > current.signal_line:
            analysis["trend"] = "bullish"
            analysis["signal_strength"] = 50
        elif current.macd_line < current.signal_line:
            analysis["trend"] = "bearish"
            analysis["signal_strength"] = -50
        
        # Histogram trend
        if len(historical) >= 3:
            recent_histograms = [h.histogram for h in historical[:3]]
            if all(recent_histograms[i] > recent_histograms[i+1] for i in range(len(recent_histograms)-1)):
                analysis["key_observations"].append("MACD histogram increasing (momentum building)")
                analysis["signal_strength"] += 10
            elif all(recent_histograms[i] < recent_histograms[i+1] for i in range(len(recent_histograms)-1)):
                analysis["key_observations"].append("MACD histogram decreasing (momentum fading)")
                analysis["signal_strength"] -= 10
        
        return analysis
    
    @staticmethod
    def analyze_rsi(
        current: RSIIndicator,
        historical: List[RSIIndicator]
    ) -> Dict[str, Any]:
        """Analyze RSI indicator"""
        analysis = {
            "zone": "neutral",
            "signal_strength": 0,
            "key_observations": []
        }
        
        # Current zone
        if current.is_overbought:
            analysis["zone"] = "overbought"
            analysis["signal_strength"] = -50
            analysis["key_observations"].append(f"RSI overbought ({current.value:.1f})")
        elif current.is_oversold:
            analysis["zone"] = "oversold"
            analysis["signal_strength"] = 50
            analysis["key_observations"].append(f"RSI oversold ({current.value:.1f})")
        elif current.is_neutral:
            analysis["zone"] = "neutral"
            analysis["signal_strength"] = 0
        
        # RSI trend
        if len(historical) >= 3:
            rsi_values = [r.value for r in historical[:3]]
            if all(rsi_values[i] > rsi_values[i+1] for i in range(len(rsi_values)-1)):
                analysis["key_observations"].append("RSI trending up")
                analysis["signal_strength"] += 10
            elif all(rsi_values[i] < rsi_values[i+1] for i in range(len(rsi_values)-1)):
                analysis["key_observations"].append("RSI trending down")
                analysis["signal_strength"] -= 10
        
        return analysis
    
    @staticmethod
    def analyze_chart_prime(chart_prime) -> Dict[str, Any]:
        """Analyze Chart Prime indicators"""
        analysis = {
            "overall_signal": "neutral",
            "signal_strength": 0,
            "key_observations": []
        }
        
        if not chart_prime:
            return analysis
        
        # Trend strength analysis
        if chart_prime.trend_strength:
            if chart_prime.trend_strength > 50:
                analysis["overall_signal"] = "bullish"
                analysis["signal_strength"] = chart_prime.trend_strength
                analysis["key_observations"].append(
                    f"Strong bullish trend (strength: {chart_prime.trend_strength})"
                )
            elif chart_prime.trend_strength < -50:
                analysis["overall_signal"] = "bearish"
                analysis["signal_strength"] = chart_prime.trend_strength
                analysis["key_observations"].append(
                    f"Strong bearish trend (strength: {chart_prime.trend_strength})"
                )
        
        # Momentum analysis
        if chart_prime.momentum_score and chart_prime.momentum_score > 70:
            analysis["key_observations"].append(
                f"High momentum ({chart_prime.momentum_score})"
            )
            analysis["signal_strength"] += 10
        
        return analysis
    
    @staticmethod
    def analyze_ema_alignment(indicators: CryptoTechnicalIndicators) -> Dict[str, Any]:
        """Analyze EMA alignment"""
        analysis = {
            "alignment": "neutral",
            "signal_strength": 0,
            "key_observations": []
        }
        
        price = indicators.close_price
        ema_20 = indicators.ema_20
        ema_50 = indicators.ema_50
        
        if not ema_20 or not ema_50:
            return analysis
        
        # Check price position relative to EMAs
        if price > ema_20 > ema_50:
            analysis["alignment"] = "bullish"
            analysis["signal_strength"] = 60
            analysis["key_observations"].append("Bullish EMA alignment (Price > EMA20 > EMA50)")
        elif price < ema_20 < ema_50:
            analysis["alignment"] = "bearish"
            analysis["signal_strength"] = -60
            analysis["key_observations"].append("Bearish EMA alignment (Price < EMA20 < EMA50)")
        elif price > ema_20:
            analysis["alignment"] = "neutral-bullish"
            analysis["signal_strength"] = 30
        elif price < ema_20:
            analysis["alignment"] = "neutral-bearish"
            analysis["signal_strength"] = -30
        
        # Check if price near EMA20 (potential support/resistance)
        if ema_20:
            distance_pct = abs(price - ema_20) / ema_20 * 100
            if distance_pct < 0.5:
                analysis["key_observations"].append("Price near EMA20 (key level)")
        
        return analysis
    
    @staticmethod
    def synthesize_technical_signals(
        current_data: TimeSeriesIndicatorData,
        historical_data: List[TimeSeriesIndicatorData]
    ) -> Dict[str, Any]:
        """Synthesize all technical signals"""
        
        # Extract historical indicators
        historical_macd = []
        historical_rsi = []
        
        for data in historical_data:
            if "macd" in data.indicators:
                macd_dict = data.indicators["macd"]
                historical_macd.append(MACDIndicator(**macd_dict))
            
            if "rsi" in data.indicators:
                rsi_dict = data.indicators["rsi"]
                historical_rsi.append(RSIIndicator(**rsi_dict))
        
        # Extract current indicators from TimeSeriesIndicatorData
        current_macd = MACDIndicator(**current_data.indicators["macd"])
        current_rsi = RSIIndicator(**current_data.indicators["rsi"])
        
        # Analyze each indicator
        macd_analysis = TradingViewTechnicalAnalyzer.analyze_macd(
            current_macd, historical_macd
        )
        rsi_analysis = TradingViewTechnicalAnalyzer.analyze_rsi(
            current_rsi, historical_rsi
        )
        
        # Chart Prime is not available in Svix API data
        chart_prime_analysis = {
            "signal": "neutral",
            "signal_strength": 50,
            "key_observations": []
        }
        
        # Convert to CryptoTechnicalIndicators for EMA analysis
        crypto_indicators = CryptoTechnicalIndicators(
            symbol=current_data.symbol,
            timestamp=current_data.timestamp,
            timeframe=current_data.timeframe,
            close_price=current_data.ohlcv["close"],
            open_price=current_data.ohlcv.get("open", current_data.ohlcv["close"]),
            high_price=current_data.ohlcv.get("high", current_data.ohlcv["close"]),
            low_price=current_data.ohlcv.get("low", current_data.ohlcv["close"]),
            volume=current_data.ohlcv["volume"],
            ema_20=current_data.indicators.get("ema_20"),
            ema_50=current_data.indicators.get("ema_50"),
            rsi=current_rsi.value,
            macd=current_macd.macd_line,
            macd_signal=current_macd.signal_line,
            macd_histogram=current_macd.histogram
        )
        
        ema_analysis = TradingViewTechnicalAnalyzer.analyze_ema_alignment(crypto_indicators)
        
        # Calculate weighted signal strength
        # MACD: 40%, RSI: 30%, Chart Prime: 20%, EMA: 10%
        total_signal_strength = (
            macd_analysis["signal_strength"] * 0.40 +
            rsi_analysis["signal_strength"] * 0.30 +
            chart_prime_analysis["signal_strength"] * 0.20 +
            ema_analysis["signal_strength"] * 0.10
        )
        
        # Determine action and direction
        if total_signal_strength > 40:
            action = OperationType.OPEN
            direction = PositionSide.LONG
        elif total_signal_strength < -40:
            action = OperationType.OPEN
            direction = PositionSide.SHORT
        else:
            action = OperationType.HOLD
            direction = PositionSide.LONG  # Default
        
        # Calculate confidence
        confidence = min(abs(total_signal_strength) / 100, 1.0)
        
        # Generate summary
        summary = TradingViewTechnicalAnalyzer._generate_technical_summary(
            macd_analysis, rsi_analysis, chart_prime_analysis, ema_analysis
        )
        
        # Collect all key factors
        key_factors = (
            macd_analysis["key_observations"] +
            rsi_analysis["key_observations"] +
            chart_prime_analysis["key_observations"] +
            ema_analysis["key_observations"]
        )
        
        return {
            "action": action,
            "direction": direction,
            "signal_strength": total_signal_strength,
            "confidence": confidence,
            "macd_analysis": macd_analysis,
            "rsi_analysis": rsi_analysis,
            "chart_prime_analysis": chart_prime_analysis,
            "ema_analysis": ema_analysis,
            "summary": summary,
            "key_factors": key_factors,
            "trend": TradingViewTechnicalAnalyzer._determine_trend(total_signal_strength)
        }
    
    @staticmethod
    def _generate_technical_summary(
        macd_analysis: Dict,
        rsi_analysis: Dict,
        chart_prime_analysis: Dict,
        ema_analysis: Dict
    ) -> str:
        """Generate human-readable technical summary"""
        parts = []
        
        # MACD
        if macd_analysis["trend"] != "neutral":
            parts.append(f"MACD shows {macd_analysis['trend']} trend")
        
        # RSI
        if rsi_analysis["zone"] != "neutral":
            parts.append(f"RSI in {rsi_analysis['zone']} zone")
        
        # Chart Prime
        if chart_prime_analysis["overall_signal"] != "neutral":
            parts.append(f"Chart Prime indicates {chart_prime_analysis['overall_signal']} bias")
        
        # EMA
        if ema_analysis["alignment"] != "neutral":
            parts.append(f"EMA alignment is {ema_analysis['alignment']}")
        
        if not parts:
            return "Technical indicators show mixed signals"
        
        return ". ".join(parts) + "."
    
    @staticmethod
    def _determine_trend(signal_strength: float) -> str:
        """Determine overall trend from signal strength"""
        if signal_strength > 40:
            return "uptrend"
        elif signal_strength < -40:
            return "downtrend"
        else:
            return "sideways"

