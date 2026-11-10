# DISTANCE rules

Keep your distance: every piece of code should know as little as possible about the others.
Full explanation with examples: https://github.com/eugeneliukindev/DISTANCE

If a rule makes the code more complex in a specific place, skip it there. When two changes both work, take the smaller one.

## Terms

- **Business logic**: entities (objects with rules, like `Order`) and use cases (one user action, like `pay_order`).
- **Infrastructure**: anything outside process memory: databases, caches, external APIs, queues, files, email, clock, randomness.
- **Adapter**: the only code that knows how one external system works. It speaks business terms outside (`orders.save(order)`) and the system's protocol inside (SQL, HTTP, Redis commands).
- **Handler**: the code the outside world calls (HTTP endpoint, CLI command, queue consumer). It parses input, calls business logic, formats output.
- **Interface**: a type with methods and no code (Protocol, interface). **Implementation**: a class that fulfills it.

## Core: check these on every change

**S1. One owner per piece of knowledge.** Every rule, threshold, format or choice lives in exactly one place; reuse it instead of repeating it. Split code by what may change, not by execution steps. Do not merge code that only looks similar but changes for different reasons.

**D1. The public API is simpler than the internals.** One call does the whole job; callers never have to know an order of steps. Extract a function or class only when it hides something and its API is simpler than the code it replaces. Length alone is not a reason to split.

**I1. Business logic does not depend on infrastructure.** Business logic never imports or calls a database client, HTTP client, cache client, file system, clock or random generator. Put each external system behind an adapter. Pass adapters in through the constructor and build them only in the entry point (`main`). Pass a single infrastructure operation (like `now()`) as a function parameter. If existing business code already calls infrastructure, that is not a pattern to copy: put every new integration in its own adapter, even when the code around it does otherwise. The adapter exists because the system's internals (schema, queries, keys, library, error codes) change often, not to swap the system.

**T1. Parse foreign data once, at the boundary.** Handlers turn request bodies into validated domain values; adapters turn rows and responses into domain values. Business logic never receives raw dicts or JSON, never reads raw keys and never validates the same thing again.

## Always, but secondary

**E1. Names say domain meaning.** Name values that carry meaning (`FREE_SHIPPING_FROM`), not their type or implementation.

**I3. Decide in pure code, act in thin code.** Compute business decisions in functions without side effects; perform payments, writes and messages afterwards in a short step. An object changing its own state is not a side effect here.

**N1. Build only what the task needs now.** No unused parameters, options, settings, plugin registries or extension points. "Might be useful" is not a reason. Generalize the shape of an API (take a `Parcel`), not its feature set.

**D2. Fewer special cases.** Define behavior so callers have nothing to handle separately: if the goal is already achieved, that is success (removing a missing item does nothing). Never hide cases the caller must react to (declined payment, out of stock).

**C1. Write the contract down.** Document in the docstring what callers need and cannot see from the signature: special cases, units, call order, errors raised.

**C2. Tests use the public API.** Tests call code the way callers do and check results. Replace infrastructure with simple fakes, not with mocks that check internal calls. Never assert on private fields.

**T2. Adapters translate foreign errors.** An adapter turns library exceptions and status codes into its own exceptions (`NetworkError` -> `PaymentUnavailable`). Business logic never catches library errors and never checks status codes.

**E2. Do the same thing the same way.** Follow how the codebase already names methods and reports "not found" and errors. If the existing way breaks S1, D1, I1 or T1, write new code correctly and say so in your reply.

**E3. Comments explain why.** Comment only reasons the code cannot show. Never restate the code.

**D3. Talk to your nearest neighbor.** Call methods on yourself, your parameters, your fields and objects you created; no `a.b().c().d()` chains through other objects' internals. When you need something from deep inside an object, add a method to the object you hold (`customer.is_gold()`) and keep the walk inside it; a new method at the end of the same chain (`customer.profile.loyalty.discount()`) is still a chain. Value objects and fluent builders are exempt.

## Only in specific situations

**A1. If a new variant of behavior appears -> add an implementation, not a branch.** A payment method or courier is a new implementation of a shared interface, chosen in the handler or entry point. No `if`/`elif`/`match` on a variant name or flag inside business logic, and no method per variant in a use case (`pay_by_cash`, `pay_by_sbp`): the use case takes the implementation (`pay(order_id, method)`). Exception: a closed, stable set with many operations (order statuses) is an enum handled completely in one owner.

**I2. If you want an interface -> add it only when a second implementation is real.** Real means: a test fake, a second provider or database, several variants right now (A1), or a replacement already decided. Otherwise depend on the class directly; extracting an interface later is a mechanical change.

**A2. If there is an interface -> every implementation fulfills the whole contract.** No `NotImplementedError`, no stronger requirements, no errors outside the contract, no `isinstance` checks by callers. If a variant cannot fulfill it, change the contract or split the interface.

**S2. If data has an invariant -> only its owner changes it.** Hide the state inside the owner; callers call methods (`order.ship(tracking)`), the owner checks the transition. Callers never assign status fields.

**A3. If you need another class's behavior -> use composition.** Hold the object in a field and call it. Inherit only from a type you fully substitute that was designed for inheritance. If existing classes inherit a helper base class (an API client, a table helper), that is not a pattern to copy: a new class takes the helper in its constructor.

**D4. If an interface has different callers -> give each a narrow one.** Each caller depends only on the methods it uses. When new code needs one or two methods of a big interface, declare a small interface with just those methods (the existing implementations already fit it) and accept that; do not pass the big one. One caller means no split.

**I4. If there are several packages -> no import cycles between them.** Break a cycle by describing a package's API in its own terms or by moving the interface to the package that uses it.

**C3. If code has no tests -> pin it first.** Before changing untested code, extract the decision into a function you can call alone, pin its current behavior with a test, then change it.
