# Model scope and scientific guarantees

## The comparison

Validity means equality of the complete declared query sets of a relaxed battery energy storage system (BESS) model and its exclusive reference. The query retains the complete net power trajectory and the variables unchanged by reconstruction. It covers all admitted queries, rather than one dispatch or one optimal objective value.

The reference is the specified mathematical device model. Its reconstruction recovers charging power, discharging power and stored energy for the declared query. It does not reconstruct unmodeled electrochemical states.

## Assumptions and implications

| Assumption | Mathematical role |
|---|---|
| The exclusive reference is contained in the relaxed feasible set | Reference queries are also admitted by the relaxation |
| Finite horizon, known initial energy and fixed deterministic dynamics | Exclusivity gives a unique energy and power reconstruction |
| Complete affine native operating constraints | Every constraint needed for reference feasibility is checked after reconstruction |
| Nonempty compact relaxed feasible set | The maximum reconstructed constraint residual is attained |
| The updated parameter state lies in a proved validity region for the same model pair and query | The complete query guarantee can be reused within that coverage |

Under these assumptions, reference feasibility of every reconstructed query is necessary and sufficient for complete query set equality. A positive residual from a verified relaxed feasible query establishes strict inclusion. Equality requires a complete argument over all admitted queries. A nonpositive floating point linear programming (LP) residual alone does not supply that argument.

Equal query sets (EQ) and strict inclusion (STRICT) are model properties. An empty relaxed feasible set is distinct from an inapplicable initialization or update in the experimental design. A timeout describes an unfinished computation, rather than a third query set relation. Later certificates preserve the original protocol records while resolving the same inputs.

## Geometry, loss and reuse

An exact convex hull preserves linear objective optima, but its projection can include a query without an exclusive realization. The midpoint construction and the statement about convex outer approximations use the same complete trajectory coordinates and declared query. They do not assert the same obstruction for arbitrary alternative representations.

Removing the common charging and discharging component removes the additional conversion loss caused by that component. Conversion losses associated with the remaining exclusive operation still apply.

A proved coverage region can be a subset of the full validity region. Leaving that coverage alone does not establish invalidity. Changes to the horizon, coefficients, native constraints or query require a guarantee covering the revised model.

## System requests and operating measurements

| Evidence | Interpretation |
|---|---|
| Three bus dispatch | Selected economic and service requests under researcher specified network extensions, device parameters and service conditions |
| Reliability Test System of the Grid Modernization Laboratory Consortium (RTS-GMLC) | A mapped 73 bus continuous direct current (DC) network model, with retained native rows and separately identified device assumptions |
| Selected numerical requests | Native constraint checks at the recorded numerical tolerances |
| Nearby exact feasible points | Exact feasibility of those points; preservation of the original complete query requires a separate check |
| Complete query set certificates | A relation between the whole projected model sets at a specified state |
| Measured operating windows | Descriptions of visited physical states; the missing native constraints and control rules prevent complete query set certification |

These system models are computational studies, not field validation. The [data guide](../DATA_GUIDE.md) defines the counting units. The [certificate guide](numerical_certificates.md) explains the scope of the executable checks.
