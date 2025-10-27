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
    def analyze_ema_alignment(
        price: float,
        ema_20: float,
        ema_50: float
    ) -> Dict[str, Any]:
        """
        Analyze EMA alignment and trend
        
        Args:
            price: Current price
            ema_20: EMA 20 value
            ema_50: EMA 50 value
            
        Returns:
            Dict with EMA analysis:
            - trend_direction: "bullish", "bearish", "neutral"
            - ema_aligned: bool
            - price_position: "above_both", "below_both", "between"
            - trend_strength: float (0-100)
            - key_observations: List[str]
        """
        analysis = {
            "trend_direction": "neutral",
            "ema_aligned": ema_20 > ema_50,
            "price_position": "between",
            "trend_strength": 0,
            "key_observations": []
        }
        
        # Price position
        price_above_20 = price > ema_20
        price_above_50 = price > ema_50
        
        if price_above_20 and price_above_50:
            analysis["price_position"] = "above_both"
        elif not price_above_20 and not price_above_50:
            analysis["price_position"] = "below_both"
        else:
            analysis["price_position"] = "between"
        
        # Trend analysis
        ema_spread_pct = abs(ema_20 - ema_50) / ema_50 * 100
        price_to_ema20_pct = abs(price - ema_20) / ema_20 * 100
        
        if analysis["ema_aligned"] and price_above_20 and price_above_50:
            analysis["trend_direction"] = "bullish"
            analysis["trend_strength"] = min(ema_spread_pct * 10 + price_to_ema20_pct * 5, 100)
            analysis["key_observations"].append(
                f"Strong bullish trend: Price above both EMAs (EMA20: ${ema_20:,.2f}, EMA50: ${ema_50:,.2f})"
            )
            if ema_spread_pct > 0.5:
                analysis["key_observations"].append(f"EMAs diverging ({ema_spread_pct:.2f}% spread)")
        
        elif not analysis["ema_aligned"] and not price_above_20 and not price_above_50:
            analysis["trend_direction"] = "bearish"
            analysis["trend_strength"] = min(ema_spread_pct * 10 + price_to_ema20_pct * 5, 100)
            analysis["key_observations"].append(
                f"Strong bearish trend: Price below both EMAs (EMA20: ${ema_20:,.2f}, EMA50: ${ema_50:,.2f})"
            )
            if ema_spread_pct > 0.5:
                analysis["key_observations"].append(f"EMAs diverging ({ema_spread_pct:.2f}% spread)")
        
        else:
            analysis["trend_direction"] = "neutral"
            analysis["trend_strength"] = 30
            if analysis["price_position"] == "between":
                analysis["key_observations"].append("Price between EMAs - potential trend change")
            if not analysis["ema_aligned"]:
                analysis["key_observations"].append("EMA bearish alignment but price action mixed")
            else:
                analysis["key_observations"].append("EMA bullish alignment but price action mixed")
        
        # Support/Resistance levels
        if price_above_20:
            analysis["key_observations"].append(f"EMA20 (${ema_20:,.2f}) acting as support")
        else:
            analysis["key_observations"].append(f"EMA20 (${ema_20:,.2f}) acting as resistance")
        
        return analysis
    
    @staticmethod
    def analyze_rsi_divergence(
        rsi7: float,
        rsi14: float
    ) -> Dict[str, Any]:
        """
        Analyze RSI7 vs RSI14 divergence
        
        Args:
            rsi7: 7-period RSI
            rsi14: 14-period RSI
            
        Returns:
            Dict with divergence analysis:
            - divergence_type: "bullish", "bearish", "neutral"
            - divergence_strength: float (0-100)
            - short_term_momentum: "stronger" or "weaker"
            - key_observations: List[str]
        """
        analysis = {
            "divergence_type": "neutral",
            "divergence_strength": 0,
            "short_term_momentum": "neutral",
            "key_observations": []
        }
        
        rsi_diff = rsi7 - rsi14
        diff_pct = abs(rsi_diff) / rsi14 * 100 if rsi14 != 0 else 0
        
        # Significant divergence threshold
        if abs(rsi_diff) > 10:
            analysis["divergence_strength"] = min(abs(rsi_diff) * 5, 100)
            
            if rsi_diff > 0:
                # RSI7 > RSI14: Short-term momentum stronger
                analysis["divergence_type"] = "bullish"
                analysis["short_term_momentum"] = "stronger"
                analysis["key_observations"].append(
                    f"Bullish divergence: RSI7 ({rsi7:.1f}) significantly above RSI14 ({rsi14:.1f})"
                )
                analysis["key_observations"].append("Short-term momentum accelerating upward")
            else:
                # RSI7 < RSI14: Short-term momentum weaker
                analysis["divergence_type"] = "bearish"
                analysis["short_term_momentum"] = "weaker"
                analysis["key_observations"].append(
                    f"Bearish divergence: RSI7 ({rsi7:.1f}) significantly below RSI14 ({rsi14:.1f})"
                )
                analysis["key_observations"].append("Short-term momentum decelerating")
        
        elif abs(rsi_diff) > 5:
            # Moderate divergence
            analysis["divergence_strength"] = abs(rsi_diff) * 5
            if rsi_diff > 0:
                analysis["divergence_type"] = "slightly_bullish"
                analysis["short_term_momentum"] = "stronger"
                analysis["key_observations"].append(f"RSI7 ({rsi7:.1f}) slightly above RSI14 ({rsi14:.1f})")
            else:
                analysis["divergence_type"] = "slightly_bearish"
                analysis["short_term_momentum"] = "weaker"
                analysis["key_observations"].append(f"RSI7 ({rsi7:.1f}) slightly below RSI14 ({rsi14:.1f})")
        
        else:
            # Aligned
            analysis["divergence_type"] = "neutral"
            analysis["short_term_momentum"] = "aligned"
            analysis["key_observations"].append(f"RSI7 and RSI14 aligned (diff: {rsi_diff:.1f})")
        
        # Zone analysis
        if rsi7 < 30 and rsi14 < 30:
            analysis["key_observations"].append("Both RSI periods in oversold zone - potential reversal")
        elif rsi7 > 70 and rsi14 > 70:
            analysis["key_observations"].append("Both RSI periods in overbought zone - potential reversal")
        elif rsi7 < 30 < rsi14:
            analysis["key_observations"].append("RSI7 entering oversold while RSI14 still neutral")
        elif rsi7 > 70 > rsi14:
            analysis["key_observations"].append("RSI7 entering overbought while RSI14 still neutral")
        
        return analysis
    
    @staticmethod
    def analyze_volatility_context(
        atr3: float,
        atr14: float,
        price: float
    ) -> Dict[str, Any]:
        """
        Analyze ATR-based volatility context
        
        Args:
            atr3: 3-period ATR (short-term)
            atr14: 14-period ATR (long-term)
            price: Current price
            
        Returns:
            Dict with volatility analysis:
            - volatility_state: "expanding", "contracting", "stable"
            - atr_ratio: float (atr3 / atr14)
            - risk_level: "high", "medium", "low"
            - suggested_stop_distance: Dict with ATR-based stops
            - key_observations: List[str]
        """
        analysis = {
            "volatility_state": "stable",
            "atr_ratio": 0,
            "risk_level": "medium",
            "suggested_stop_distance": {},
            "key_observations": []
        }
        
        if atr14 == 0:
            return analysis
        
        atr_ratio = atr3 / atr14
        analysis["atr_ratio"] = atr_ratio
        
        # Volatility state
        if atr_ratio > 1.3:
            analysis["volatility_state"] = "rapidly_expanding"
            analysis["risk_level"] = "high"
            analysis["key_observations"].append(
                f"Volatility rapidly expanding: ATR3 ({atr3:.2f}) is {(atr_ratio-1)*100:.1f}% above ATR14 ({atr14:.2f})"
            )
        elif atr_ratio > 1.1:
            analysis["volatility_state"] = "expanding"
            analysis["risk_level"] = "elevated"
            analysis["key_observations"].append(
                f"Volatility expanding: ATR3 ({atr3:.2f}) above ATR14 ({atr14:.2f})"
            )
        elif atr_ratio < 0.7:
            analysis["volatility_state"] = "contracting"
            analysis["risk_level"] = "low"
            analysis["key_observations"].append(
                f"Volatility contracting: ATR3 ({atr3:.2f}) well below ATR14 ({atr14:.2f})"
            )
        elif atr_ratio < 0.9:
            analysis["volatility_state"] = "slightly_contracting"
            analysis["risk_level"] = "low-medium"
            analysis["key_observations"].append(
                f"Volatility slightly contracting: ATR3 ({atr3:.2f}) below ATR14 ({atr14:.2f})"
            )
        else:
            analysis["volatility_state"] = "stable"
            analysis["risk_level"] = "medium"
            analysis["key_observations"].append(
                f"Volatility stable: ATR3 ({atr3:.2f}) and ATR14 ({atr14:.2f}) aligned"
            )
        
        # ATR as percentage of price
        atr3_pct = (atr3 / price * 100) if price > 0 else 0
        atr14_pct = (atr14 / price * 100) if price > 0 else 0
        
        analysis["key_observations"].append(
            f"ATR3: {atr3_pct:.2f}% of price, ATR14: {atr14_pct:.2f}% of price"
        )
        
        # Suggested stop distances (ATR-based)
        analysis["suggested_stop_distance"] = {
            "conservative": {
                "atr_multiple": 2.5,
                "distance": atr14 * 2.5,
                "stop_price_long": price - (atr14 * 2.5),
                "stop_price_short": price + (atr14 * 2.5),
                "risk_pct": (atr14 * 2.5 / price * 100) if price > 0 else 0
            },
            "moderate": {
                "atr_multiple": 2.0,
                "distance": atr14 * 2.0,
                "stop_price_long": price - (atr14 * 2.0),
                "stop_price_short": price + (atr14 * 2.0),
                "risk_pct": (atr14 * 2.0 / price * 100) if price > 0 else 0
            },
            "aggressive": {
                "atr_multiple": 1.5,
                "distance": atr3 * 1.5,
                "stop_price_long": price - (atr3 * 1.5),
                "stop_price_short": price + (atr3 * 1.5),
                "risk_pct": (atr3 * 1.5 / price * 100) if price > 0 else 0
            }
        }
        
        # Trading implications
        if analysis["risk_level"] == "high":
            analysis["key_observations"].append("⚠️  High volatility: Consider reducing position size")
        elif analysis["risk_level"] == "low":
            analysis["key_observations"].append("✓ Low volatility: Favorable for larger positions")
        
        return analysis
    
    @staticmethod
    def analyze_macd_momentum(
        current_macd: MACDIndicator,
        historical_macd: List[MACDIndicator]
    ) -> Dict[str, Any]:
        """
        Analyze MACD momentum and trend changes
        
        Args:
            current_macd: Current MACD values
            historical_macd: Historical MACD values (most recent first)
            
        Returns:
            Dict with MACD momentum analysis:
            - momentum_direction: "strengthening", "weakening", "stable"
            - histogram_trend: "increasing", "decreasing", "flat"
            - crossover_potential: bool
            - signal_quality: "strong", "moderate", "weak"
            - key_observations: List[str]
        """
        analysis = {
            "momentum_direction": "stable",
            "histogram_trend": "flat",
            "crossover_potential": False,
            "signal_quality": "moderate",
            "key_observations": []
        }
        
        if len(historical_macd) < 3:
            return analysis
        
        # Histogram trend analysis
        hist_values = [current_macd.histogram] + [h.histogram for h in historical_macd[:4]]
        
        # Check if histogram is consistently increasing/decreasing
        increasing_bars = sum(1 for i in range(len(hist_values)-1) if hist_values[i] > hist_values[i+1])
        decreasing_bars = sum(1 for i in range(len(hist_values)-1) if hist_values[i] < hist_values[i+1])
        
        if increasing_bars >= 3:
            analysis["histogram_trend"] = "increasing"
            analysis["momentum_direction"] = "strengthening"
            if current_macd.histogram > 0:
                analysis["key_observations"].append("Bullish momentum strengthening (histogram increasing)")
                analysis["signal_quality"] = "strong"
            else:
                analysis["key_observations"].append("Bearish momentum weakening (histogram rising toward zero)")
        
        elif decreasing_bars >= 3:
            analysis["histogram_trend"] = "decreasing"
            analysis["momentum_direction"] = "weakening"
            if current_macd.histogram < 0:
                analysis["key_observations"].append("Bearish momentum strengthening (histogram decreasing)")
                analysis["signal_quality"] = "strong"
            else:
                analysis["key_observations"].append("Bullish momentum weakening (histogram falling toward zero)")
        
        else:
            analysis["histogram_trend"] = "flat"
            analysis["momentum_direction"] = "stable"
            analysis["signal_quality"] = "weak"
            analysis["key_observations"].append("MACD momentum choppy or consolidating")
        
        # Crossover potential
        macd_diff = current_macd.macd_line - current_macd.signal_line
        prev_diff = historical_macd[0].macd_line - historical_macd[0].signal_line
        
        if abs(macd_diff) < abs(prev_diff) * 0.3:  # Lines converging
            analysis["crossover_potential"] = True
            if macd_diff > 0:
                analysis["key_observations"].append("⚠️  MACD lines converging - potential bearish crossover ahead")
            else:
                analysis["key_observations"].append("⚠️  MACD lines converging - potential bullish crossover ahead")
        
        # Current state
        if current_macd.is_bullish_crossover:
            analysis["key_observations"].append("✓ Fresh bullish MACD crossover detected")
            analysis["signal_quality"] = "strong"
        elif current_macd.is_bearish_crossover:
            analysis["key_observations"].append("✓ Fresh bearish MACD crossover detected")
            analysis["signal_quality"] = "strong"
        
        # Histogram magnitude
        hist_abs = abs(current_macd.histogram)
        prev_hist_abs = abs(historical_macd[0].histogram)
        
        if hist_abs > prev_hist_abs * 1.5:
            analysis["key_observations"].append(f"Strong momentum surge (histogram: {current_macd.histogram:.4f})")
        
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
            "overall_signal": "neutral",
            "signal_strength": 0,
            "key_observations": []
        }
        
        # Get current values for enhanced analysis
        price = current_data.ohlcv.get("price", current_data.ohlcv.get("close", 0))
        ema_20 = current_data.indicators.get("ema_20")
        ema_50 = current_data.indicators.get("ema_50")
        rsi7 = current_data.indicators.get("rsi7")
        rsi14 = current_data.indicators.get("rsi14")
        atr3 = current_data.indicators.get("atr3")
        atr14 = current_data.indicators.get("atr14")
        
        # === Enhanced Analysis (new) ===
        
        # MACD Momentum
        macd_momentum_analysis = TradingViewTechnicalAnalyzer.analyze_macd_momentum(
            current_macd, historical_macd
        ) if historical_macd else {}
        
        # EMA Alignment
        ema_analysis = TradingViewTechnicalAnalyzer.analyze_ema_alignment(
            price, ema_20, ema_50
        ) if (ema_20 and ema_50) else {"alignment": "neutral", "signal_strength": 0, "key_observations": []}
        
        # RSI Divergence (RSI7 vs RSI14)
        rsi_divergence_analysis = TradingViewTechnicalAnalyzer.analyze_rsi_divergence(
            rsi7, rsi14
        ) if (rsi7 and rsi14) else {}
        
        # Volatility Context
        volatility_analysis = TradingViewTechnicalAnalyzer.analyze_volatility_context(
            atr3, atr14, price
        ) if (atr3 and atr14) else {}
        
        # Calculate weighted signal strength (updated weights with new indicators)
        # MACD: 35%, RSI: 25%, EMA: 20%, Volatility: 10%, Chart Prime: 10%
        ema_signal = ema_analysis.get("trend_strength", 0) if "trend_direction" in ema_analysis else ema_analysis.get("signal_strength", 0)
        if ema_analysis.get("trend_direction") == "bearish":
            ema_signal = -ema_signal
        
        total_signal_strength = (
            macd_analysis["signal_strength"] * 0.35 +
            rsi_analysis["signal_strength"] * 0.25 +
            ema_signal * 0.20 +
            chart_prime_analysis["signal_strength"] * 0.10
        )
        
        # Adjust for volatility context
        if volatility_analysis:
            if volatility_analysis.get("risk_level") == "high":
                total_signal_strength *= 0.8  # Reduce signal strength in high volatility
            elif volatility_analysis.get("risk_level") == "low":
                total_signal_strength *= 1.1  # Boost signal strength in low volatility
        
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
        
        # Collect all key factors (including new analyses)
        key_factors = (
            macd_analysis["key_observations"] +
            rsi_analysis["key_observations"] +
            chart_prime_analysis["key_observations"] +
            ema_analysis.get("key_observations", [])
        )
        
        # Add enhanced analysis key observations
        if macd_momentum_analysis:
            key_factors.extend(macd_momentum_analysis.get("key_observations", []))
        if rsi_divergence_analysis:
            key_factors.extend(rsi_divergence_analysis.get("key_observations", []))
        if volatility_analysis:
            key_factors.extend(volatility_analysis.get("key_observations", []))
        
        return {
            "action": action,
            "direction": direction,
            "signal_strength": total_signal_strength,
            "confidence": confidence,
            # Core analysis
            "macd_analysis": macd_analysis,
            "rsi_analysis": rsi_analysis,
            "chart_prime_analysis": chart_prime_analysis,
            "ema_analysis": ema_analysis,
            # Enhanced analysis (Phase 2)
            "macd_momentum_analysis": macd_momentum_analysis,
            "rsi_divergence_analysis": rsi_divergence_analysis,
            "volatility_analysis": volatility_analysis,
            # Summary
            "summary": summary,
            "key_factors": key_factors[:15],  # Limit to top 15 factors
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
        
        # EMA - support both old and new formats
        if "trend_direction" in ema_analysis:
            # New format
            if ema_analysis["trend_direction"] != "neutral":
                parts.append(f"EMA shows {ema_analysis['trend_direction']} trend")
        elif "alignment" in ema_analysis:
            # Old format
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

