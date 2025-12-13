# Session Contracts: A Relative-Value Derivative for Information Extraction and Robust Settlement

## Abstract

This note proposes a new class of derivatives, **session contracts**, that create a closed, fully-collateralised “micro-market” on a fixed basket of underlying assets over a time window $[t_1, t_2]$.  
Instead of trading each asset against cash (USD), participants only trade **allocation between assets** inside the session. At maturity, the session’s total collateral is allocated according to final market prices of the underlying assets.

We show how this design:

- isolates **relative-value views** (e.g. AAPL vs TSLA) rather than absolute USD views,
- naturally generates **high-signal order-flow data** when participation is restricted to more sophisticated investors,
- is structurally convenient for **stress testing** and risk analysis due to full collateralisation and a closed value pool,
- and differs from existing instruments such as pairs-trading strategies, spread options and prediction/pair-mutuel markets.

Mathematically, the contract is formulated with a finite set of underlyings and conservation constraints on total holdings, and can be generalised from two assets to an $n$-asset basket using basic linear algebra.

---

## 1. Motivation

Classical equity markets can be viewed as one giant “session” where every asset is priced in a numeraire (usually USD), and trading is organised as many asset–USD pairs (AAPL–USD, TSLA–USD, etc.).

However, many use-cases are **inherently relative**:

- “Is AAPL rich vs TSLA?”
- “Is semiconductor beta overpriced vs broad tech?”
- “Is stock $i$ mis-priced relative to a sector basket?”

These questions are commonly implemented through **pairs trading** or statistical arbitrage, where portfolios are constructed to be approximately market-neutral and profit from mean reversion in spreads. :contentReference[oaicite:0]{index=0}

At the same time, there is a separate literature on **prediction markets** and **pari-mutuel market microstructure**, showing that well-designed contingent-claim markets can aggregate dispersed information efficiently and generate data useful for forecasting and policy. :contentReference[oaicite:1]{index=1}

Session contracts can be seen as combining elements of:

- *relative-value* trading (pairs/stat-arb),
- *information markets* (prediction/pari-mutuel),
- and *fully collateralised* risk transfer,

but implemented directly on listed equities (or other underlyings) with a clean, finite time horizon.

---

## 2. Contract Definition

### 2.1 Basic two-asset example

Consider two stocks, AAPL and TSLA.  
Fix a session from time $t_1$ to maturity $t_2$.

Define a **basket vector of shares**:
\[
q = (q_{\text{AAPL}}, q_{\text{TSLA}}) = (100, 100).
\]

Let $S_t = (S_t^{\text{AAPL}}, S_t^{\text{TSLA}})$ be the vector of spot prices in USD at time $t$. The **total USD value** of the basket at time $t$ is
\[
V_t = q \cdot S_t = 100 S_t^{\text{AAPL}} + 100 S_t^{\text{TSLA}}.
\]

A **session contract** is defined as:

1. **Initial collateralisation**

   - At $t_1$, a session organiser (exchange, clearing house, or a special-purpose vehicle) holds the physical basket $q$ or its fully funded cash equivalent.
   - The basket (or its USD value) is *ring-fenced* for this session only.

2. **Session tokens**

   - The organiser issues a fixed number $N$ of **session tokens**.  
   - Holding one token corresponds to a claim on $\frac{1}{N}$ of the total basket $q$ at maturity (or its cash equivalent).

3. **Allocation vectors**

   - Each participant $i$ at time $t \in [t_1,t_2]$ holds an **allocation vector**
     \[
     x_i(t) = \big(x_{i,\text{AAPL}}(t), x_{i,\text{TSLA}}(t)\big),
     \]
     interpreted as the number of AAPL and TSLA shares they are effectively entitled to if the session were to settle at time $t$.
   - The system satisfies the **conservation constraint**
     \[
     \sum_i x_i(t) = q \quad \text{for all } t.
     \]
     Total claims always equal the underlying basket.

4. **Trading rule**

   - During the session, participants may **trade only reallocations** of $x_i(t)$ among themselves.  
   - Any trade is a zero-sum transfer:
     \[
     \Delta x_i(t) = - \sum_{j \neq i} \Delta x_j(t).
     \]
   - There is **no direct trading vs USD inside the session**. USD only enters to pay transaction fees or initial premium for entering the session.

5. **Payoff at maturity**

   - At $t_2$, the session is settled. Participant $i$ receives:
     - either delivery of shares $x_i(t_2)$,
     - or cash settlement $\pi_i = x_i(t_2) \cdot S_{t_2}$ in USD.
   - Because of the conservation constraint, the sum of all payoffs equals the basket value:
     \[
     \sum_i \pi_i = q \cdot S_{t_2} = V_{t_2}.
     \]

Participants with a bullish view on AAPL vs TSLA will try to increase $x_{i,\text{AAPL}}$ at the expense of $x_{i,\text{TSLA}}$; the opposite holds for the other side. There is no net inflow or outflow of USD inside the session; USD value is only redistributed through the relative price movement of AAPL and TSLA.

### 2.2 Generalisation to $n$ assets

Let the session be defined on $n$ underlyings:

- Basket vector $q \in \mathbb{R}^n_+$,
- Price vector $S_t \in \mathbb{R}^n_+$,
- Total session value $V_t = q^\top S_t$.

Each participant $i$ holds an allocation vector
\[
x_i(t) \in \mathbb{R}^n, \quad \sum_i x_i(t) = q.
\]

At maturity, participant $i$’s payoff is
\[
\pi_i = x_i(t_2)^\top S_{t_2}.
\]

The **feasible set** of allocations is the hyperplane
\[
\mathcal{X} = \left\{ (x_i)_i : \sum_i x_i = q \right\} \subset \mathbb{R}^{n \times m},
\]
where $m$ is the number of participants. Trading is any continuous path within $\mathcal{X}$.

We can also re-parameterise in terms of **weight vectors**
\[
w_i(t) = \frac{1}{q_{\text{tot}}} x_i(t) \odot q^{-1}, 
\]
where $\odot$ denotes elementwise multiplication and $q_{\text{tot}} = \sum_k q_k$. Then $w_i(t)$ lives in a simplex and represents the fraction of the basket (in units of underlying shares) that investor $i$ controls.

---

## 3. Basic Mathematical Properties

### 3.1 Zero-sum property inside a fixed-value pool

For any time $t$,
\[
\sum_i x_i(t) = q \quad \Rightarrow \quad \sum_i x_i(t)\cdot S_t = q \cdot S_t = V_t.
\]

Total session value equals the basket value; trading only redistributes this among participants.

Define the **mark-to-market P&L** of investor $i$ relative to some baseline allocation $\bar{x}_i$ (e.g. equal weights) as
\[
\text{PnL}_i(t) = \big(x_i(t) - \bar{x}_i\big) \cdot S_t.
\]

Summing over all investors:
\[
\sum_i \text{PnL}_i(t) = \left(\sum_i x_i(t) - \sum_i \bar{x}_i\right)\cdot S_t
= (q - q)\cdot S_t = 0.
\]

So the game is **strictly zero-sum** in terms of deviations from the baseline allocation.

### 3.2 Relative-price dynamics as state variables

For the two-asset case, the economically relevant state is the **price ratio**
\[
R_t = \frac{S_t^{\text{AAPL}}}{S_t^{\text{TSLA}}}.
\]

Any allocation $x_i(t)$ can be mapped to exposure to $R_t$. For example, in the 2-asset case we can write
\[
x_i(t) = \big(\alpha_i(t) q_{\text{AAPL}}, (1-\alpha_i(t)) q_{\text{TSLA}}\big),
\]
with $\alpha_i(t)\in\mathbb{R}$ and $\sum_i \alpha_i(t) = 1$.  
The payoff difference vs a neutral allocation depends on changes in $R_t$, not on the absolute level of USD.

In the $n$-asset case, the relevant objects are **relative price vectors**, e.g.
\[
\tilde{S}_t^k = \frac{S_t^k}{S_t^1}, \quad k=2,\dots,n,
\]
or any other choice of numeraire. The session contracts effectively create bets on these relative states.

### 3.3 Volatility and information content

Because the session only redistributes a fixed value $V_t$, the “price” of a marginal unit of AAPL vs TSLA inside the session is a **relative price** determined purely by participants’ beliefs and risk preferences, not by funding constraints in USD.

Intuitively, this can produce:

- **Higher effective volatility** in the session-implied AAPL/TSLA ratio (or allocation weights) than in each stock’s standalone USD price.
- A cleaner mapping from **trades to relative beliefs** (less noise from funding, margin calls, or index flows).

Microstructure models (e.g. Kyle (1985)) show that when informed traders interact with noise traders, order flow conveys information and prices become more informative. :contentReference[oaicite:2]{index=2}  
A session that restricts participation to more sophisticated investors (e.g. by minimum capital or professional status) can increase the *signal-to-noise ratio* of the observed order flow, making it valuable as a dataset.

---

## 4. Relation to Existing Instruments

### 4.1 Pairs trading and relative-value arbitrage

Classical **pairs trading** constructs a long/short portfolio between two assets (or between an asset and a basket) and profits when the spread converges. Gatev, Goetzmann and Rouwenhorst (2006) document that simple distance-based pairs trading rules historically generated significant excess returns, showing that such relative mispricings exist and can be systematically exploited. :contentReference[oaicite:3]{index=3}

Key differences vs session contracts:

- Pairs trading is usually implemented *in the main market* using margin and external funding.  
  Session contracts instead create a **separate, fully collateralised micro-market** on a fixed basket.
- Pairs trading P&L depends on *both* relative mispricing and the trader’s funding/margin constraints; session P&L is purely redistributive inside the basket.
- Pairs trading leaves no explicit record of “who thought AAPL vs TSLA should be where” beyond trade logs in the main market; the session creates a **self-contained dataset** of allocation trajectories and order books.

### 4.2 Spread and basket options

Spread options (e.g. payoff on $S_T^1 - S_T^2$) and basket options (payoff on $\sum_k w_k S_T^k$) also target relative or multi-asset exposures. However:

- Their payoffs are usually **single-time, function-of-terminal-state** claims, not path-dependent reallocations of a fixed pool.
- They are often written vs a dealer, with counterparty risk and margin.

Session contracts instead:

- enforce **value conservation** ($\sum_i x_i = q$) at all times,
- and treat the dealer/organiser as a neutral custodian rather than a risk-taking counterparty.

### 4.3 Prediction markets and pari-mutuel mechanisms

Prediction markets trade contingent claims on future events (e.g. elections), and a large literature shows they can aggregate dispersed information effectively, often outperforming polls. :contentReference[oaicite:4]{index=4}

Pari-mutuel and related mechanisms organise such trading in a way that bounds the organiser’s risk and aggregates bets into state-contingent prices. :contentReference[oaicite:5]{index=5}

Session contracts are similar in that:

- there is a **closed pool of collateral**,
- payoffs depend on the realised state (here, the vector of final prices $S_{t_2}$),
- prices inside the session aggregate participants’ beliefs.

They differ in two crucial ways:

1. The state space is **continuous and high-dimensional** (all possible joint prices of the equities), not a small discrete set of outcomes.
2. The payoff is not a fixed \$1 if event $i$ occurs, but a **linear claim** on the underlying assets.

This makes session contracts a kind of “relative-value information market” directly linked to listed securities.

---

## 5. Risk Management and Stress Testing

Regulators and risk managers use **stress testing** to assess how portfolios behave under adverse scenarios (e.g. large moves, correlation breakdowns). Basel Committee principles emphasise clear scenario design, transparency of risk transfer and robust modelling of correlation and liquidity effects. :contentReference[oaicite:6]{index=6}

Session contracts help here in several ways:

1. **Full collateralisation & clear exposure**

   - The basket $q$ (or its cash equivalent) is fully funded at inception.
   - Exposure of each participant at any time is a simple linear function of $S_t$: $\pi_i = x_i(t)\cdot S_t$.
   - This makes scenario P&L under stress (e.g. $S_{t_2} = S_{t_1} + \Delta S$) a straightforward matrix multiplication.

2. **Controlled, ring-fenced leverage**

   - Because the session is zero-sum and bounded by $V_t$, aggregate exposure cannot exceed the basket value.
   - External leverage is possible (participants borrowing to buy session tokens), but *inside* the contract, leverage is structurally bounded.

3. **Scenario design in relative terms**

   - Many stress scenarios are naturally stated in relative terms (“large underperformance of growth vs value”, “energy rally vs broad market”).
   - Session contracts are built exactly on these **relative axes**, so stress tests can be specified directly in the relevant coordinates (e.g. shocks to price ratios or relative sector moves).

4. **Data for model validation**

   - The time series of allocation vectors $\{x_i(t)\}$, session order books, and implied “session prices” provide rich data to validate risk models for relative-value strategies, liquidity and crowding.

---

## 6. Economic Uses and Benefits

### 6.1 Higher-quality information signals

If the platform restricts participation by:

- professional qualifications,
- minimum capital,
- track record,

then the order flow in each session is likely to reflect **better-informed views** than retail-dominated main markets.  

In microstructure terms, the fraction of “informed” to “noise” traders is higher, making order flow more informative about fundamentals. :contentReference[oaicite:7]{index=7}

The resulting dataset (anonymised as needed) can be:

- sold to institutions,
- used to calibrate relative-value models,
- or used internally by market makers and risk managers to infer term structures of relative value (e.g. implied “fair” AAPL/TSLA ratio over a given horizon).

### 6.2 Increased effective volatility and trading opportunities

Because trading is purely in **allocations**, not in absolute wealth, small changes in beliefs about relative value can cause large swings in session-implied prices (e.g. the “price” in AAPL vs TSLA units that clears supply and demand).

For quantitative strategies, this means:

- more **return variation** to harvest inside the session,
- while the external basket value $V_t$ may be comparatively stable.

In other words, the contract **amplifies relative-value volatility** while keeping absolute risk bounded by the basket.

### 6.3 Safer settlement structure

The contract has natural safeguards:

- Fully collateralised underlying basket $q$ or cash equivalent.
- No need for the organiser to take directional risk; they act as custodian and rule-enforcer.
- Settlement is a straightforward allocation of existing assets or cash.

This contrasts with some OTC derivatives or CFD structures where the dealer may be exposed to client default and must manage complex margin processes.

### 6.4 Research, DeFi, and market structure applications

Potential longer-term applications include:

- **Academic research** on belief dynamics, herding and information diffusion in relative-value space, using clean session data.
- **DeFi/Web3 implementations**, where each session is tokenised, and allocation vectors are represented by on-chain balances subject to conservation constraints.
- **Market design experiments**, e.g. using automated market makers or convex cost-function mechanisms (as in prediction markets) inside the session to maintain continuous liquidity. :contentReference[oaicite:8]{index=8}

---

## 7. Practical Design Choices and Risks

A few non-trivial design questions remain:

- **Liquidity fragmentation**:  
  Splitting trading into many small sessions may fragment liquidity away from the main market. Design must balance information gain vs fragmentation costs.

- **Regulatory treatment**:  
  Depending on jurisdiction, session contracts may be classified as derivatives, pooled investment vehicles, or prediction-like markets; each has its own regulatory regime.

- **Adverse selection and manipulation**:  
  Sophisticated participants might attempt to use the session both to profit inside and to manipulate expectations outside. Controls on transparency, position limits and monitoring are needed.

- **Session design**:  
  - Which baskets $q$ are allowed? (Sector, themes, factor proxies…)  
  - How long should the time window $[t_1, t_2]$ be?  
  - Should sessions roll (like futures) or be single-shot?

These choices can be optimised using simulation and empirical backtesting once some pilot data exists.

---

## 8. Conclusion

Session contracts provide a relatively simple mathematical structure:

- a fixed, fully collateralised basket $q$,
- conservation of total claims $\sum_i x_i = q$,
- linear payoffs $\pi_i = x_i(t_2)\cdot S_{t_2}$,

but with a different *market organisation* compared with standard equity trading.

By forcing trading to occur only as reallocations within a closed pool, they:

- isolate **relative-value beliefs**,
- create **informative, low-noise datasets** when participation is curated,
- and offer a **transparent, stress-test-friendly** framework for transferring risk.

From the perspective of an MFE-level toolkit, the mathematics is straightforward (linear algebra, basic stochastic price processes), but the economic and market-design implications are rich: session contracts sit at the intersection of relative-value arbitrage, prediction markets, and robust risk transfer.

---

## References

- Agrawal, S., Wang, Y., & Ye, Y. (2009).  
  *A Unified Framework for Dynamic Pari-Mutuel Information Market Design.* In Proceedings of the 10th ACM Conference on Electronic Commerce. :contentReference[oaicite:9]{index=9}  

- Basel Committee on Banking Supervision. (2018).  
  *Stress Testing Principles.* Bank for International Settlements. :contentReference[oaicite:10]{index=10}  

- Gatev, E., Goetzmann, W. N., & Rouwenhorst, K. G. (2006).  
  *Pairs Trading: Performance of a Relative-Value Arbitrage Rule.* Review of Financial Studies, 19(3), 797–827. :contentReference[oaicite:11]{index=11}  

- Kyle, A. S. (1985).  
  *Continuous Auctions and Insider Trading.* Econometrica, 53(6), 1315–1335. :contentReference[oaicite:12]{index=12}  

- Wolfers, J., & Zitzewitz, E. (2004).  
  *Prediction Markets.* Journal of Economic Perspectives, 18(2), 107–126. :contentReference[oaicite:13]{index=13}  
