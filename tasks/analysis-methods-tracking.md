# Analysis Methods Tracking - For MCP Implementation

**Purpose**: Track analysis methods used in palladium investigation for future MCP tool development

**Context**: Henry Decsi (first user) - precious metals PM, short vol positioning

---

## Analysis Methods Used (Palladium Investigation Oct 2025)

### 1. Multi-Timeframe Factor Decomposition

**What it does:** Separate beta (market factors) from idio (security-specific) returns across different timeframes

**Implementation:**
```python
# Multi-factor regression (OLS)
# Y = α + β₁X₁ + β₂X₂ + ... + βₙXₙ + ε
# Where ε (residual) = idiosyncratic component

# Factors used:
factors = {
    'GLD': 'Gold (safe haven)',
    'TLT': '20Y Treasury Bonds (rates)',
    'SPY': 'S&P 500 (equity market)',
    'COPX': 'Copper/Industrial (industrial demand)',
    'SLV': 'Silver (precious metal)'
}

# Three timeframes:
# 1. 1-Year baseline (248 obs) - long-term factor structure
# 2. 1-Month recent (20 obs) - regime detection
# 3. Single event (Oct 17) - event attribution using both models

# Output metrics:
# - R² (variance explained by factors)
# - Beta coefficients for each factor
# - Idio Vol (annualized standard deviation of residuals)
# - Total Vol, Explained Vol
# - Residual analysis (what % was idio vs beta)
```

**Key insight from palladium:**
- 1Y baseline: 33% R² (mostly idio)
- 1M regime: 60% R² (regime shift detected - gold beta 5x increase!)
- Oct 17 event: 60-68% idio (majority NOT explained by macro)

**MCP tool signature (proposed):**
```python
factor_decomposition(
    symbol: str,           # e.g., 'PALL'
    factors: list[str],    # e.g., ['GLD', 'TLT', 'SPY', 'COPX', 'SLV']
    timeframes: list[str]  # e.g., ['1Y', '1M', 'event:2025-10-17']
) -> FactorAnalysis
```

**Output structure:**
```
FACTOR DECOMPOSITION - PALL

1-YEAR BASELINE (248 observations)
R² = 0.333 (33% explained by factors, 67% idio)
Idio Vol: 28.1% (ann)
Factor Betas:
  Silver (SLV):   +0.650  ← Dominant
  Gold (GLD):     +0.196
  Bonds (TLT):    +0.047
  Equity (SPY):   +0.013
  Industrial:     -0.035

1-MONTH RECENT REGIME (20 observations)
R² = 0.602 (60% explained by factors, 40% idio)
Idio Vol: 41.6% (ann)
Factor Betas (vs 1Y):
  Gold (GLD):     +1.020  (1Y: +0.196) ← 5x INCREASE (REGIME CHANGE!)
  Silver (SLV):   +0.440  (1Y: +0.650)
  Equity (SPY):   -0.239  (1Y: +0.013) ← FLIPPED NEGATIVE
  ...

OCT 17 EVENT ATTRIBUTION
Actual: -10.16%
1Y Model Predicted: -3.21% (32% explained, 68% idio)
1M Model Predicted: -3.99% (39% explained, 61% idio)

Factor Contributions (1M model):
  Gold:       -1.92%
  Silver:     -1.95%
  Equity:     -0.14%
  Industrial: -0.10%
  Bonds:      +0.01%
  Total Beta: -3.99%
  Idio:       -6.18% ← PALLADIUM-SPECIFIC

Data as of 2025-10-27 | Source: yfinance
```

**Why this matters for Henry:**
- Position sizing based on idio vol (Paleologo framework)
- Regime detection (beta structure changed recently!)
- Event attribution (was it macro or security-specific?)

---

### 2. Options Chain Analysis

**What it does:** Analyze complete option chain for positioning, sentiment, vol structure

**Implementation:**
```python
# Get option chain
ticker = yf.Ticker('PALL')
dates = ticker.options  # List of expiration dates
chain = ticker.option_chain(dates[0])  # Nearest expiration

# Analyze positioning
calls = chain.calls
puts = chain.puts

# Metrics calculated:
# - Put/Call ratio (volume, open interest)
# - Largest positions by OI
# - Implied volatility by strike
# - Vol skew (OTM puts vs ATM)
# - Recent activity (by volume)
```

**Key insight from palladium:**
- OI P/C 0.51 = bullish positioning (2x calls vs puts)
- $160 calls with 1,186 OI crushed (now $30 underwater)
- Call IV > Put IV (unusual - typically puts have premium)
- Flat vol skew = no panic

**MCP tool signature (proposed):**
```python
options_analysis(
    symbol: str,       # e.g., 'PALL'
    expiration: str    # e.g., 'nearest' or '2025-11-21'
) -> OptionsAnalysis
```

**Output structure:**
```
PALL US EQUITY                          OPTIONS DATA

NEAREST EXPIRY: 2025-11-21 (25 days)
Current Price: $130.28

POSITIONING
Put/Call Ratio (Vol):  0.88  (Slightly more calls)
Put/Call Ratio (OI):   0.51  (BULLISH - 2x calls vs puts)

TOP POSITIONS (Open Interest)
Calls:
  $160:  1,186 OI    $30 underwater  ← Largest, crushed
  $150:    918 OI    $20 underwater
  $140:    832 OI    $10 underwater
  $130:    207 OI    ATM (82 vol - recent defense)

Puts:
  $115:    486 OI    $15 OTM
  $116:    451 OI
  $110:    255 OI

IMPLIED VOLATILITY
ATM Calls:     57.4%
ATM Puts:      53.8%
Spread:        +3.6% calls  (UNUSUAL - calls bid up)

VOL SKEW
OTM Puts vs ATM: +0.3%  (Flat - no panic premium)

Data as of 2025-10-27 | Source: yfinance
Back: ticker('PALL')
```

**Why this matters for Henry:**
- He's short vol (needs to know positioning, IV levels)
- Bullish positioning crushed = gamma squeeze potential
- Vol structure (term structure, skew) = convexity context

---

### 3. Volatility Analysis (Realized vs Implied)

**What it does:** Compare realized historical volatility vs implied (options market)

**Implementation:**
```python
# Calculate realized vol (multiple windows)
returns = ticker.history(period='1y')['Close'].pct_change()

rv_7d = returns.rolling(7).std() * np.sqrt(252)   # 7-day annualized
rv_30d = returns.rolling(30).std() * np.sqrt(252) # 30-day annualized

# Get implied vol from ATM options
iv_atm = chain.calls[chain.calls['strike'] == atm_strike]['impliedVolatility'].values[0]

# Calculate spreads
rv_iv_spread_30d = rv_30d - iv_atm
rv_iv_spread_7d = rv_7d - iv_atm

# Vol term structure (from multiple expirations)
# Near-term, mid-term, long-term IV
# Contango = near_iv - far_iv (positive = vol expected to compress)
```

**Key insight from palladium:**
- RV 7d: 90.2% (extreme, includes Oct 17)
- RV 30d: 58.5% (elevated but more normal)
- IV ATM: 57.4%
- **RV (30d) vs IV: +1.1%** (vol fairly priced on 30d)
- **RV (7d) vs IV: +32.8%** (realized spiked far above implied - gamma pain)
- Term structure contango: +10.3% (market expects compression)

**MCP tool signature (proposed):**
```python
volatility_analysis(
    symbol: str,
    windows: list[str] = ['7d', '30d']  # Realized vol windows
) -> VolatilityAnalysis
```

**Output structure:**
```
PALL US EQUITY                          VOLATILITY ANALYSIS

REALIZED VOL (Annualized)
7-Day:     90.2%   (Extreme - recent spike)
30-Day:    58.5%   (Elevated)

IMPLIED VOL (From Options)
ATM (24d): 57.4%

RV vs IV SPREADS
30-Day RV vs IV:  +1.1%   (Vol fairly priced)
7-Day RV vs IV:  +32.8%   (Realized exceeds implied - gamma pain!)

VOL TERM STRUCTURE
Near-term (24d):   57.4%
Mid-term (52d):    53.4%
Long-term (143d):  47.1%

Contango: +10.3%  (Near - Far)  ← Market expects compression

INTERPRETATION
Market pricing vol to compress from 57% → 47% over time.
But current realized (7d) at 90% = short vol positions bleeding.

Data as of 2025-10-27 | Source: yfinance
Back: ticker('PALL')
```

**Why this matters for Henry:**
- Short vol positions: RV > IV = losing money (gamma > theta)
- Term structure contango = market expects compression (supports short vol thesis)
- But bleeding now until compression happens

---

### 4. Event Attribution (Single-Day Decomposition)

**What it does:** Decompose a specific event using pre-trained factor models

**Implementation:**
```python
# Use pre-trained models (1Y baseline, 1M regime)
# Apply to single event returns

# Oct 17 returns:
oct17_returns = {
    'PALL': -0.1016,
    'GLD': -0.0188,
    'TLT': -0.0015,
    'SPY': +0.0057,
    'COPX': -0.0241,
    'SLV': -0.0443
}

# Predict using 1Y model
X_oct17 = [oct17_returns['GLD'], oct17_returns['TLT'], ...]
predicted_1y = model_1y.predict(X_oct17)
residual_1y = oct17_returns['PALL'] - predicted_1y

# Predict using 1M model
predicted_1m = model_1m.predict(X_oct17)
residual_1m = oct17_returns['PALL'] - predicted_1m

# Factor contributions (decompose prediction)
for factor in factors:
    contribution = beta[factor] * oct17_returns[factor]
```

**Key insight from palladium:**
- Oct 17: -10.16% total
- 1Y model: -3.21% beta, -6.95% idio (68% idio!)
- 1M model: -3.99% beta, -6.18% idio (61% idio!)
- Even with regime change, majority was palladium-specific

**MCP tool signature (proposed):**
```python
event_attribution(
    symbol: str,
    event_date: str,           # e.g., '2025-10-17'
    factor_models: list[str]   # e.g., ['1Y', '1M']
) -> EventAttribution
```

**Output structure:**
```
OCT 17 EVENT ATTRIBUTION - PALL

ACTUAL RETURNS (Oct 17, 2025)
PALL (Palladium): -10.16%  ← The event
GLD (Gold):       -1.88%
TLT (Bonds):      -0.15%
SPY (Equity):     +0.57%   (Risk-on)
COPX (Industrial):-2.41%
SLV (Silver):     -4.43%

USING 1-YEAR MODEL (Baseline Betas)
Predicted (beta): -3.21%
Actual:           -10.16%
Residual (idio):  -6.95%
Beta explains:     31.6% of move
Idio explains:     68.4% of move  ← MAJORITY PALLADIUM-SPECIFIC

Factor Contributions:
  Silver:       -2.88%
  Gold:         -0.37%
  Industrial:   +0.08%
  Equity:       +0.01%
  Bonds:        -0.01%
  Total Beta:   -3.21%

USING 1-MONTH MODEL (Recent Regime)
Predicted (beta): -3.99%
Actual:           -10.16%
Residual (idio):  -6.18%
Beta explains:     39.2% of move
Idio explains:     60.8% of move  ← STILL MAJORITY IDIO

Factor Contributions:
  Gold:         -1.92%  (Higher due to 1.02 beta in recent regime)
  Silver:       -1.95%
  Equity:       -0.14%
  Industrial:   -0.10%
  Bonds:        +0.01%
  Total Beta:   -3.99%

KEY FINDING
Even accounting for recent regime change, 61-68% of Oct 17 move
was NOT explained by macro factors. Something palladium-specific
drove the majority of the -10.16% drop.

Data as of 2025-10-27 | Source: yfinance
```

**Why this matters for Henry:**
- Tells you if move was macro (beta) or security-specific (idio)
- Informs whether to hedge or ride it out
- Critical for short vol: Is this systematic risk or idio event?

---

## Additional Factors Available via yfinance (VALIDATED)

**From palladium investigation - factors we tested and validated:**

| Factor | Symbol | Type | What It Captures | Validated? |
|--------|--------|------|------------------|------------|
| **Platinum** | PPLT | Commodity | Substitution relationship, PGM correlation | ✓ HUGE (+19.4% R²) |
| **USD Strength** | UUP | Currency | Dollar strength (inverse for commodity prices) | ✓ Small (+1.5% R²) |
| Auto stocks | GM, F | Equity | Auto production proxy | ✗ NO EFFECT (stocks ≠ production) |
| China equity | FXI | Equity | China demand proxy | ✗ NO EFFECT (doesn't capture auto) |

**Key learnings:**
1. **Commodity relationships matter** - PPLT was the KEY missing factor for palladium
2. **Equity proxies don't work** - GM/F stocks don't capture ICE production volumes
3. **Broad country ETFs don't work** - FXI doesn't capture sector-specific demand

**For other commodities, consider testing:**
- Related commodity substitutes (e.g., Natural Gas vs Oil, Corn vs Wheat)
- Currency effects (UUP for dollar strength)
- Industry-specific ETFs (not broad country ETFs)

---

## Philosophy: Maximum Context, Not Recommendations

**The real value:** Give the analyst as much context as needed/possible. Let THEM decide.

**NOT:**
- ❌ "Should you buy/sell/hold?"
- ❌ "The trade is CORRECT but EARLY"
- ❌ "Cover if price breaks $126"

**YES:**
- ✓ "60-68% of Oct 17 move was idio (not explained by macro factors)"
- ✓ "Regime changed: Gold beta 5x increase, equity beta flipped negative"
- ✓ "Platinum is the missing factor: +19.4% R² improvement"
- ✓ "RV (90%) >> IV (57%) = gamma exceeding theta"
- ✓ "Bullish positioning crushed: OI P/C 0.51, $160 calls 1,186 OI underwater"

**Then the analyst (Henry) decides:**
- Does this support or refute my thesis?
- Should I size up, hold, or cover?
- Is this explainable or unknown risk?

**MCP tools should be CONTEXT DELIVERY SYSTEMS.**

---

## Implementation Priority (For MCP)

**Phase 1 - Context Screens (High Priority):**
1. ✅ `ticker(symbol)` - Individual security screen (basic version exists)
2. ❌ `options_analysis(symbol)` - Complete option chain analysis
   - Positioning (OI P/C, largest strikes)
   - IV structure (ATM, skew, term structure)
   - Recent activity (volume, flow)
   - **Context, not recommendation**

3. ❌ `volatility_analysis(symbol)` - RV vs IV, term structure
   - Realized vol (7d, 30d windows)
   - Implied vol (ATM, term structure, skew)
   - RV vs IV spreads (is gamma exceeding theta?)
   - Historical comparison (current vs typical)
   - **Context, not prediction**

4. ❌ `factor_analysis(symbol, factors)` - Beta vs idio decomposition
   - R² (how much explained by factors?)
   - Factor betas (what's driving moves?)
   - Idio vol (stock-specific risk for position sizing)
   - Multi-timeframe (detect regime changes)
   - **Include additional factor testing** (PPLT for PALL, etc.)
   - **Context, not prediction**

**Phase 2 - Event Context:**
5. ❌ `event_attribution(symbol, date)` - Single-day decomposition
   - Was this move beta or idio?
   - Which factors contributed?
   - Consistent with historical sensitivities?
   - **Explain what happened, not what to do**

6. ❌ `regime_detection(symbol, factors)` - Factor structure changes
   - Are betas stable or shifting?
   - Compare recent vs baseline factor structure
   - Flag when regime changes detected
   - **Alert to instability, not predict direction**

**Phase 3 - Relational Context:**
7. ❌ `correlation_matrix(symbols, period)` - Cross-asset relationships
   - Pairwise correlations
   - Rolling correlations (stability check)
   - Identify related assets
   - **Show relationships, not trades**

8. ❌ `related_factors(symbol)` - Suggest testable factors
   - Commodity substitutes (PPLT for PALL)
   - Currency effects (UUP)
   - Sector-specific (not broad country ETFs)
   - **Exploratory context, not prescriptive**

**Phase 4 - Position Context (IF analyst provides details):**
9. ❌ `position_context(symbol, position_details)` - Greeks, P&L calculation
   - Calculate theta, gamma, vega from position details
   - Current P&L estimation
   - RV vs IV comparison for short vol
   - **Show math, not advice** ("Your gamma is $X per 1% move" NOT "You should cover")

10. ❌ `convexity_context(symbol)` - Theta vs gamma analysis
    - Is realized vol exceeding implied?
    - Theta collection vs gamma losses
    - Term structure implications
    - **Numbers, not judgment** ("Theta $X/day, gamma cost $Y on 1% moves" NOT "This is bad")

---

## Design Principle: Context Dense, Judgment Sparse

**Every MCP tool should:**
1. ✓ Show complete data (comprehensive context)
2. ✓ Calculate metrics (save analyst time)
3. ✓ Highlight key findings (what stands out)
4. ✓ Show historical comparison (is this normal or unusual?)
5. ✓ Flag regime changes / instability (when assumptions break)
6. ❌ NEVER say "buy/sell/hold"
7. ❌ NEVER say "this is good/bad"
8. ❌ NEVER predict future ("vol will compress")

**Format:**
- Dense BBG Lite tables (scannable, professional)
- Key findings bolded (draw attention to important context)
- Interpretation inline (explain what metrics MEAN, not what to DO)
- Explicit uncertainties (say what we DON'T KNOW)
- Navigation affordances (drill down for more context)

**Example good output:**
```
PALL US EQUITY                    VOLATILITY ANALYSIS

REALIZED VOL (Annualized)
7-Day:     90.2%   ← Extreme spike (Oct 17 event)
30-Day:    58.5%
Historical avg (1Y): 34.4%

IMPLIED VOL (From Options)
ATM (24d): 57.4%

RV vs IV SPREADS
30-Day RV vs IV:  +1.1%   (Vol fairly priced on 30d)
7-Day RV vs IV:  +32.8%   (Realized exceeds implied - gamma pain for short vol)

VOL TERM STRUCTURE
Near (24d):  57.4%
Mid (52d):   53.4%
Far (143d):  47.1%
Contango: +10.3%  (Market pricing compression)

INTERPRETATION
- Recent realized (90%) far above implied (57%)
- For short vol: Gamma losses exceeding theta collection
- Term structure suggests market expects compression to 47%
- But no timeframe for when compression occurs

Data as of 2025-10-27 | Source: yfinance
Back: ticker('PALL')
```

**NOT:**
```
RECOMMENDATION: COVER SHORT VOL POSITION
- RV >> IV is dangerous for short vol
- You should exit before more losses
- Price target: Cover at $126
```

---

## What This Means for Implementation

**Priority 1:** Build context screens that compress analysis time

Henry currently spends 3 hours gathering context:
- Options data from Bloomberg
- Historical vol calculations manually
- Factor research (correlations, drivers)
- Cross-checking multiple sources

**Goal:** Compress 3 hours → 5 minutes with comprehensive context screens

**Priority 2:** Maximum context density (BBG Lite format)

Each screen should answer:
- What's happening now? (current state)
- Is this normal? (historical comparison)
- What's driving it? (factor attribution)
- What's uncertain? (explicit gaps in knowledge)

**Priority 3:** NO recommendations, NO predictions

Trust the analyst to synthesize context and make decisions.
Our job: Deliver complete, accurate, timely context.
Their job: Decide what to do with it.

---

## Validation: Did We Provide Good Context?

**From palladium investigation:**

✓ **What we gave Henry:**
- Factor decomposition (60-68% idio, not macro)
- Platinum is missing factor (+19.4% R²)
- Regime change (betas shifted dramatically)
- Options positioning (bullish crushed, OI P/C 0.51)
- Vol structure (RV >> IV, term structure contango)
- Event attribution (Oct 17 breakdown)

✓ **What we avoided:**
- ❌ NO "should you cover?"
- ❌ NO "the trade is wrong"
- ❌ NO "this will happen next"

✓ **Result:**
- Comprehensive context delivered
- Evidence-based (all claims validated)
- Explicit uncertainties stated
- Analyst decides based on context + their thesis

**This is the template for all MCP tools.**

---

## Data Requirements

**Already available in yfinance:**
- ✅ Historical prices (`.history()`)
- ✅ Options chains (`.options`, `.option_chain(date)`)
- ✅ Basic ticker info (`.info`, `.fast_info`)

**Need to calculate:**
- ❌ Realized volatility (rolling windows, annualized)
- ❌ Factor regressions (multi-factor OLS)
- ❌ Vol term structure (from multiple expirations)
- ❌ Vol skew (OTM vs ATM IV)
- ❌ Greeks (delta, gamma, theta, vega) - can derive from Black-Scholes
- ❌ Idio vol (residual volatility from factor model)

**Libraries needed:**
- numpy (linear algebra, lstsq for regression)
- pandas (data manipulation)
- scipy (stats, optimize for Black-Scholes)
- yfinance (data source)

---

## BBG Lite Formatting Principles

**Learned from palladium investigation:**

1. **Dense, scannable** - No fluff, lots of info in small space
2. **Tables with alignment** - Right-align numbers, left-align labels
3. **Visual hierarchy** - Headers, sections, indentation
4. **Key findings bolded** - `**68.4% idio**` stands out
5. **Interpretation inline** - `← MAJORITY PALLADIUM-SPECIFIC` (explain, don't just show data)
6. **Navigation affordances** - `Back: ticker('PALL')`, `Drill down: sector('metals')`
7. **Timestamp + source** - `Data as of 2025-10-27 | Source: yfinance`
8. **Explicit uncertainties** - Say what you DON'T know
9. **No recommendations** - Evidence only, let user decide

---

## User Feedback Context (Henry's Needs)

**What Henry is looking for:**
- He's an options PM (25+ years experience)
- Short vol positioning (first time in his life)
- Company wants bigger swings (size up)
- Has Bloomberg terminal (doesn't need data, needs ANALYSIS)
- Talks about convexity a lot
- Uses "codex + BBG" as reference

**What he asked for:**
- "Explain palladium changes in last week"

**What we delivered:**
- Detective investigation (crime scene approach)
- Multi-timeframe factor decomposition
- Options positioning analysis
- Vol structure (RV vs IV, term structure, skew)
- Event attribution (beta vs idio)
- NO RECOMMENDATIONS (evidence only)

**What worked:**
- Evidence-first approach (no speculation)
- Factor decomposition (separates beta from idio - critical for Paleologo)
- Multi-timeframe analysis (regime detection)
- Complete option chain analysis (positioning, sentiment)
- Explicit uncertainties (say what we don't know)

**What's next:**
- Build these methods into MCP tools
- Expose options functionality
- Build synthesis layer (interpret findings for user)
- Position sizing integration (Paleologo framework)

---

## Technical Notes

**Regression implementation (numpy, no sklearn):**
```python
# Manual OLS regression (no external dependencies beyond numpy)
X = np.column_stack([np.ones(len(factors)), factor_returns])  # Add intercept
y = security_returns

# Solve: beta = (X'X)^-1 X'y
XtX = X.T @ X
Xty = X.T @ y
beta = np.linalg.solve(XtX, Xty)

# Predictions and residuals
y_pred = X @ beta
residuals = y - y_pred

# R-squared
ss_res = np.sum(residuals**2)
ss_tot = np.sum((y - np.mean(y))**2)
r_squared = 1 - (ss_res / ss_tot)

# Volatilities (annualized)
total_vol = np.std(y) * np.sqrt(252)
idio_vol = np.std(residuals) * np.sqrt(252)
```

**Why no sklearn:**
- Keep dependencies minimal
- OLS is simple enough to implement manually
- More transparent (can explain to users)
- Faster for small regressions

**Timezone handling:**
```python
# yfinance returns timezone-aware datetimes
# Use pd.Timestamp().tz_localize(returns.index.tz) for comparisons
start_1m = pd.Timestamp(end_date - timedelta(days=30)).tz_localize(returns.index.tz)
mask_1m = returns.index >= start_1m
```

---

**This is infrastructure, not a side project.**

Track what works. Build what's proven. Ship to Henry.
