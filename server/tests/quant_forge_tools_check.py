from fractions import Fraction as F

def hr(t): print("\n=== " + t + " ===")

hr("1. BURN MULTIPLE")
new, exp, churn, contr = 180_000, 30_000, 45_000, 15_000
net_new_arr = new + exp - churn - contr
cash_out, cash_in = 600_000, 150_000
net_burn = cash_out - cash_in
print("net new ARR =", new, "+", exp, "-", churn, "-", contr, "=", net_new_arr)
print("net burn    =", cash_out, "-", cash_in, "=", net_burn)
print("burn multiple = %d / %d = %.4f" % (net_burn, net_new_arr, net_burn/net_new_arr))
# cross-check: net new ARR must equal ending - starting
print("cross-check (ending-starting ARR) =", (1_350_000 - 1_200_000), "== net_new_arr?", (1_350_000-1_200_000)==net_new_arr)
print("monthly-average variant: burn/3 = %.2f, ARR/3 = %.2f, ratio = %.4f" % (net_burn/3, net_new_arr/3, (net_burn/3)/(net_new_arr/3)))

hr("2. DILUTION  (exact share-count model)")
def round_dilution(founders, pool_now, V_pre, R, pool_target):
    T = founders + pool_now
    # solve E + dP = p*(T + dP + N),  N = R*(T+dP)/V_pre
    # => (E+dP)(1 - p*(1+R/V_pre)) = p*T   ... derive:
    # E+dP = p*(T+dP) + p*N = p*(T+dP) + p*R*(T+dP)/V_pre
    # E+dP = p*(T+dP)*(1+R/V_pre)
    k = 1 + R/V_pre
    dP = (pool_target*T*k - pool_now) / (1 - pool_target*k)
    dP = max(0.0, dP)
    N  = R*(T+dP)/V_pre
    post = T + dP + N
    return dP, N, post, N/post, founders/post, (pool_now+dP)/post
base = round_dilution(8_000_000, 1_000_000, 8_000_000, 2_000_000, 0.0)
print("no pool change: dP=%.0f N=%.0f post=%.0f investor%%=%.4f founder%%=%.4f" % base[:5])
d = round_dilution(8_000_000, 1_000_000, 8_000_000, 2_000_000, 0.12)
print("pool to 12%%:     dP=%.0f N=%.0f post=%.0f investor%%=%.4f founder%%=%.4f pool%%=%.4f" % d)
# independent brute-force check: same math, solved by iteration on price
def brute(founders, pool_now, V_pre, R, pool_target):
    dP = 0.0
    for _ in range(200):
        T = founders+pool_now+dP
        price = V_pre/T
        N = R/price
        post = T+N
        cur_pool = (pool_now+dP)/post
        dP += (pool_target - cur_pool)*post   # move pool toward target
    return dP, N, post
bd = brute(8_000_000, 1_000_000, 8_000_000, 2_000_000, 0.12)
print("brute-force check: dP=%.0f N=%.0f post=%.0f  (matches algebra: %s)" % (bd[0], bd[1], bd[2], abs(bd[2]-d[2])<1))
# simple no-pool reduction: investor% = R/(V_pre+R)
print("simple check R/(V_pre+R) = %.4f" % (2_000_000/(8_000_000+2_000_000)))
# cumulative multi-round dilution, Carta medians
chain = [0.19, 0.18, 0.15]
keep = 1.0
for c in chain: keep *= (1-c)
print("cumulative keep (0.81*0.82*0.85) = %.6f -> cumulative dilution = %.4f" % (keep, 1-keep))
keep_c = 1.0
for c in [0.20,0.20,0.16,0.096]: keep_c *= (1-c)
print("2021 chain (0.80*0.80*0.84*0.904) = %.6f -> dilution = %.4f" % (keep_c, 1-keep_c))

hr("3. LTV:CAC")
arpa, gm, churn_m = 500.0, 0.80, 0.02
sm_spend, new_cust = 120_000.0, 24
ltv = arpa*gm/churn_m
cac = sm_spend/new_cust
print("LTV = %.0f * %.2f / %.2f = %.2f" % (arpa, gm, churn_m, ltv))
print("CAC = %.0f / %d = %.2f" % (sm_spend, new_cust, cac))
print("LTV:CAC = %.4f" % (ltv/cac))
print("CAC payback months = CAC/(ARPA*GM) = %.2f / %.2f = %.4f" % (cac, arpa*gm, cac/(arpa*gm)))
print("annual-churn form: LTV = ARPA_annual*GM/annual_churn = %.0f*%.2f/%.24f = %.2f" % (arpa*12, gm, 0.24, arpa*12*gm/0.24))

hr("4. EDGE CASES (machine output)")
def bm(net_burn, net_new_arr):
    if net_new_arr == 0: return "undefined (no new ARR): division by zero"
    r = net_burn/net_new_arr
    return "%.4f" % r
print("bm burn=300k arr=0      ->", bm(300_000, 0))
print("bm burn=300k arr=-50k   ->", bm(300_000, -50_000), "(shrinking: negative, not 'efficient')")
print("bm burn=-20k arr=100k   ->", bm(-20_000, 100_000), "(cash-flow positive: clamp to 0 / 'n/a')")
print("bm burn=0    arr=100k   ->", bm(0, 100_000))
def dil(V_pre, R):
    if V_pre + R <= 0: return "undefined (post-money <= 0)"
    return "investor%% = %.4f" % (R/(V_pre+R))
print("dil V_pre=0 R=2m        ->", dil(0, 2_000_000), "(all-raise round: investors get 100%)")
print("dil V_pre=-1m R=2m      -> investor%% = %.4f (negative pre-money: nonsense input)" % (2_000_000/( -1_000_000+2_000_000)))
print("dil V_pre=8m R=0        ->", dil(8_000_000, 0))
print("dil V_pre=1m R=-2m      ->", dil(1_000_000, -2_000_000))
def ltv_cac(arpa, gm, churn, sm, cust):
    out=[]
    if churn <= 0: out.append("LTV undefined/infinite (churn = 0): needs a cap")
    else: out.append("LTV = %.2f" % (arpa*gm/churn))
    if cust <= 0: out.append("CAC undefined (0 new customers)")
    elif sm <= 0: out.append("CAC = 0 -> ratio undefined")
    else: out.append("CAC = %.2f" % (sm/cust))
    return "; ".join(out)
print("ltv churn=0             ->", ltv_cac(500,0.8,0,120_000,24))
print("ltv gm=0                ->", ltv_cac(500,0.0,0.02,120_000,24))
print("ltv cust=0              ->", ltv_cac(500,0.8,0.02,120_000,0))
print("ltv sm=0                ->", ltv_cac(500,0.8,0.02,0,24))
print("ltv churn=0.5 (50%/mo)  ->", ltv_cac(500,0.8,0.5,120_000,24))

hr("5. ANNUAL vs MONTHLY CHURN TRAP")
m = 0.02
annual_compound = 1 - (1-m)**12
print("monthly churn 2%% -> compounded annual churn = %.6f (%.2f%%)" % (annual_compound, annual_compound*100))
print("naive 12*2%% = 24%% ; LTV with 24%% = %.2f ; LTV with compounded = %.2f ; difference = %.1f%%"
      % (6000*0.8/0.24, 6000*0.8/annual_compound, (6000*0.8/annual_compound)/(6000*0.8/0.24)*100-100))
hr("6. POOL TARGET UNREACHABLE CASE")
def pool_dP(T, E, V_pre, R, p):
    k = 1 + R/V_pre
    den = 1 - p*k
    if den <= 0: return "NO SOLUTION (p*k = %.4f >= 1): pool target unreachable at this raise size" % (p*k)
    return "dP = %.2f" % max(0.0, (p*T*k - E)/den)
print("p=0.12, V_pre=8m, R=2m ->", pool_dP(9_000_000, 1_000_000, 8_000_000, 2_000_000, 0.12))
print("p=0.90, V_pre=8m, R=2m ->", pool_dP(9_000_000, 1_000_000, 8_000_000, 2_000_000, 0.90))
print("p=0.05 (pool already above target) ->", pool_dP(9_000_000, 1_000_000, 8_000_000, 2_000_000, 0.05))
