# Proposal: aligning OIC change/expiry/revocation with ZTL logical time

**From:** the ZTL side (Vitaly Reznik, ZTL semantic boundary owner).
**For:** open item *"epoch, expiry, revocation, and anti-tick mapping"* in the architecture disposition on PR #2.
**Standing:** a concrete proposal, not an invitation to discuss. The measured facts in §3 hold whether or not OIC adopts this vocabulary; the mapping in §4 is a **proposed interpretation** and needs a joint conformance test before either side relies on it.

---

## 1. Why this needs an explicit decision

OIC already has a temporal apparatus: effective periods, supersession, amendment, revocation, change propagation, re-admission, historical replay. ZTL has one too, machine-checked on an empty axiom list. If the two are left implicit, the system will carry **two independent notions of time** that agree by accident — and disagree exactly where it is expensive: when a control that was "settled" has to be re-opened.

## 2. The ZTL model, stated plainly

ZTL has **no physical clock** and is blind to duration. Its only clock is the **arrival of ground**:

- **tick** = one act of verification, `verify(mark → earned value)`: an atom moves Z → T or Z → F.
- **moment** = a marking (which atoms are currently grounded).
- **past** = the verified prefix; **future** = the *tree* of possible verifications, since each remaining Z can resolve either way. Branching time, not a line: "everyone's time differs" means different traces through one tree.
- **anti-tick** = `expire(marking, atom)`: a grounded atom returns to Z. Ground is *withdrawn* — a registry re-checked, a document lapsed, an authority revoked.

The three warranty grades are, exactly, three temporal quantifiers:

| Grade | Temporal reading |
|---|---|
| `until-verification` | true **now** (credit) |
| `sound` | true **at every ending** (all completed traces agree; the road may wobble) |
| `hereditary` | true **always, along every path** (invariant of the whole tree) |

## 3. Three measured facts that constrain any design

These are reproducible from the pinned corpus (`ztime.py`, `zexpire.py`), not architectural opinions.

### 3.1 `hereditary` is absorbing — under monotone refinement only

Exhaustive over all depth-≤2 formulas on two atoms: **2,906 formulas, 29,812 ticks, 0 violations** of "a hereditary verdict never moves under a tick". Also measured: `until-verification → hereditary` direct jumps exist (14,818 — ground can arrive all at once), `sound → until-verification` demotions exist (108), and **no compound formula ever sits at value Z** (greedy collapse in temporal costume). Of 130 completed traces, **all 130 end hereditary**: the arrow of logical time points at the shelf.

**The trap:** this absorbing property is about *more ground arriving*. It says nothing about ground being **taken away**. Reading `hereditary` as "settled forever, no re-check needed" is the single most attractive wrong interpretation of our warranty ladder, and it is wrong against expiry, revocation, correction, source invalidation, schema change, semantic-version change and admissibility change.

### 3.2 Unrestricted expiry trivialises warranties

Small theorem, plus a measured census over the same exhaustive pool. From any marking, the operations `{expire, verify}` reach **every** marking (expire everything, then verify to the target — a two-line construction). Therefore "invariant under refinement **and** arbitrary expiry" means "constant over all markings" — a **frame**: a test that cannot fail and therefore proves nothing. In the census, only constant-verdict formulas survive unrestricted expiry; every contentful assertion loses its shelf.

**Consequence for OIC:** if any ground may expire at any time by any authority, the whole warranty apparatus degrades into decoration. Expiry must be **scoped** — declared, not ambient.

### 3.3 Scoped expiry has a price, and the price is computable ("expiry-insurance")

Measured on the worked example (a vehicle purchase). Declare *which* atoms carry a clock: the dealer warranty is voidable (∈ E), the title papers are not (∉ E).

- A verdict settled early by a shortcut — `T/hereditary` at tick 2, "saving" two checks — **unsettles** when the clock runs out: `T/hereditary → F/until-verification`.
- But if those two "saved" checks are **paid before the clock runs out**, the same expiry leaves the verdict standing: T survives, the grade merely softens.

So the checks the optimiser "saved" were never free: they are the deal's **expiry-insurance**, and the kernel prices it. An OIC control that is cheap to admit today may be exactly the one that collapses on the first revocation.

## 4. Proposed mapping (needs your confirmation)

| OIC event | ZTL operation | Consequence we can compute |
|---|---|---|
| evidence supplied / fact confirmed | `verify`: Z → T/F (**tick**) | new verdict + grade; possible early settlement |
| source amendment creating a new version | `expire` of affected atoms, then re-verify | the affected dependency set (which controls must be re-admitted) |
| revocation of authority or evidence | `expire` (**anti-tick**) | verdicts that lose their shelf, with the exact atoms responsible |
| effective period lapses | `expire` scheduled on declared atoms | which controls are insured against it and which are not |
| correction | `expire` + re-verify, history preserved | the reliance that must be re-examined |
| historical replay | evaluate at the marking of that moment | the same verdict and grade as then, reproducibly |

**What we would need in the envelope to make this operational:** a declaration, per required fact, of whether it is **expirable** and under whose authority — the `E` set of §3.3. Without it we can still compute verdicts, but we cannot tell you *which of your controls are insured against revocation and which will unsettle*, which is the part worth having.

## 5. What we are not proposing

- We are **not** asking OIC to adopt ZTL's vocabulary in its own documents.
- We are **not** claiming that logical time replaces institutional time (effective dates, jurisdictional validity, retention). Ours is the order in which *grounds* arrive and depart; yours is the calendar of institutions. They are different clocks and both are needed.
- We are **not** offering a scheduler. ZTL has no physical clock; something on your side must decide *when* a thing expires. We can only say what that does to the warrant.

## 6. What we ask

1. Confirm or correct §4, in particular whether `expire` is the right model for your revocation and amendment paths.
2. Tell us whether the envelope can carry the expirable-fact declaration of §3.3. If it cannot, say so — we would rather narrow the claim than assume the field exists.
3. If OIC's `hereditary`-equivalent is ever displayed to a reviewer, please carry the qualifier from §3.1 with it. A grade shown without its scope will be read as "settled forever" by the first person in a hurry.

---

*Nothing here asserts that ZTL has been independently reproduced. The facts in §3 are measured on the pinned corpus and reproducible by command; the mapping in §4 is proposed, not settled.*
