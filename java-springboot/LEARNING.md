# Learning GraminSahay (Spring Boot for Java developers)

This guide teaches you the Spring Boot concepts used in **this project**, assuming you
already know Java but are new to Spring Boot. Every concept is tied to a real file in the
repo, so reading this *is* studying your own project. By the end you'll be able to explain
GraminSahay confidently in an interview.

Read it top to bottom once, then keep it open while you read the actual code.

---

## 0. The one-sentence mental model

> **Spring Boot is just Java + a helper that creates and connects your objects for you,
> and turns some of your classes into a running web server.**

You still write plain Java classes. Spring Boot's job is to:
1. **Create objects for you** (so you don't write `new SomeService(...)` everywhere), and
2. **Wire them together** (hand each object the other objects it needs), and
3. **Run a web server** that maps HTTP requests to your methods.

That's genuinely most of it. The rest is details.

---

## 1. Beans and the "application context"

A **bean** = an object that Spring creates and manages for you.

When the app starts, Spring builds a big registry of beans called the **application
context**. Your job is to *mark* which classes should become beans; Spring does the rest.

You mark a class as a bean with a **stereotype annotation**:

| Annotation | Means "this is a..." | In this project |
|---|---|---|
| `@RestController` | web endpoint handler | `NavigatorController` |
| `@Service` | business-logic class | `NavigatorService`, `SchemeRetriever`, `AnswerGenerator`, `SchemeIngestionService` |
| `@Component` | generic managed object | `EligibilityEngine`, `ConflictDetector` |
| `@Repository` | data-access class | `SchemeRepository` |

> 💡 **Interview-ready fact:** `@Service`, `@Component`, and `@Repository` are *functionally
> almost identical* — they all make the class a bean. The different names are just for
> readability (they document the class's **role**). `@Repository` additionally translates
> some database exceptions.

**Look at:** the top of `EligibilityEngine.java` — the single line `@Component` is what
tells Spring "create one of these and keep it ready for anyone who needs it."

---

## 2. Dependency Injection (DI) — the most important concept

This is the heart of Spring. It sounds fancy; it's simple.

**Without Spring**, if `NavigatorService` needs an `EligibilityEngine`, you'd write:
```java
EligibilityEngine engine = new EligibilityEngine(); // you create it yourself
```

**With Spring**, you just *ask* for it in the constructor, and Spring hands it to you:
```java
public NavigatorService(EligibilityEngine eligibilityEngine, ...) {
    this.eligibilityEngine = eligibilityEngine; // Spring passed it in
}
```

This is called **constructor injection**. Spring sees that `NavigatorService` needs an
`EligibilityEngine`, finds the `EligibilityEngine` bean it already created, and passes it in
automatically. You never call `new` for your beans.

**Why it matters (say this in interviews):**
- Classes don't create their own dependencies → they're **loosely coupled**.
- You can swap a dependency for a fake one in **tests** (see §8).
- Spring manages object lifecycle, so you focus on logic.

**Look at:** the constructor of `NavigatorService.java` — it asks for four beans
(`SchemeRetriever`, `EligibilityEngine`, `ConflictDetector`, `AnswerGenerator`). Spring
injects all four. That constructor *is* dependency injection.

> 💡 Note: when a class has exactly **one** constructor, Spring injects into it
> automatically — you don't even need an `@Autowired` annotation. That's why you won't see
> `@Autowired` anywhere in this project; the modern style omits it.

---

## 3. The entry point: `@SpringBootApplication`

**Look at:** `GraminSahayApplication.java`

```java
@SpringBootApplication
public class GraminSahayApplication {
    public static void main(String[] args) {
        SpringApplication.run(GraminSahayApplication.class, args);
    }
}
```

- `@SpringBootApplication` is three annotations in one. The important effect:
  **"component scan"** — Spring scans this package (`in.graminsahay`) and every sub-package,
  finds all your `@Service`/`@Component`/`@RestController`/`@Repository` classes, and turns
  them into beans automatically.
- `SpringApplication.run(...)` boots everything: starts the embedded web server (Tomcat),
  builds the application context, and wires all beans.

That's why you don't configure a server anywhere — Spring Boot ships one inside the app.

---

## 4. Making a web API: `@RestController`

**Look at:** `web/NavigatorController.java`

```java
@RestController
@RequestMapping("/api")
public class NavigatorController {

    @PostMapping("/navigate")
    public NavigationResponse navigate(@Valid @RequestBody NavigateRequest request) { ... }
}
```

Line by line:
- `@RestController` — this class handles HTTP requests and returns data (not web pages).
  Spring automatically converts your returned Java object to **JSON**.
- `@RequestMapping("/api")` — base path for every method in the class.
- `@PostMapping("/navigate")` — this method handles `POST /api/navigate`.
- `@RequestBody NavigateRequest request` — Spring reads the JSON in the request body and
  converts it into a `NavigateRequest` object for you (the reverse of returning JSON).
- `@Valid` — before your method runs, Spring checks the validation rules on
  `NavigateRequest` (see §5). If they fail, it returns a 400 error automatically.

**The flow:** HTTP JSON in → `NavigateRequest` object → your method → `NavigationResponse`
object → HTTP JSON out. You only write the middle part.

---

## 5. Request objects and validation (DTOs)

**Look at:** `web/NavigateRequest.java`

A **DTO** (Data Transfer Object) is just a simple class that models the shape of a request
or response. This project uses Java **records** for them (concise, immutable).

```java
public record NavigateRequest(
        @NotBlank(message = "situation is required") String situation,
        String occupation,
        ...
) { }
```

- `@NotBlank` is a **Bean Validation** rule — combined with `@Valid` in the controller, it
  rejects requests where `situation` is empty, automatically, before your code runs.
- The `toProfile()` method converts the incoming request into a domain object
  (`CitizenProfile`) — keeping web concerns (the request shape) separate from domain logic.

> 💡 **Design point for interviews:** notice the project separates **web DTOs**
> (`NavigateRequest`) from **domain models** (`CitizenProfile`, `Scheme`). This is good
> layering: the API shape can change without touching core logic.

---

## 6. Configuration: `application.yml` and `@Value`

**Look at:** `src/main/resources/application.yml` and the fields in `SchemeRetriever.java`

Instead of hard-coding settings, Spring Boot reads them from `application.yml` at startup.

```yaml
graminsahay:
  rag:
    top-k: 6
```

Then any bean can inject that value:
```java
@Value("${graminsahay.rag.top-k:6}")
private int topK;   // becomes 6
```
- `${...}` reads a property from `application.yml` (or an environment variable).
- The `:6` after the key is a **default** used if the property is missing.

Environment variables also flow in: `${OPENAI_API_KEY:changeme}` means "use the
`OPENAI_API_KEY` env var, or `changeme` if it's not set." That's how your API key stays out
of the code.

---

## 7. Auto-configuration & starters (the "magic", explained)

**Look at:** `pom.xml`

You added dependencies like:
```xml
<artifactId>spring-ai-pgvector-store-spring-boot-starter</artifactId>
```

A **"starter"** is a bundle of related libraries plus **auto-configuration**:
- Because the pgvector starter is on the classpath *and* you set `spring.ai.vectorstore...`
  properties in `application.yml`, Spring Boot **automatically creates a `VectorStore` bean**
  for you — connected to your Postgres, with the right table and index.
- Same for the OpenAI starter: it creates a `ChatClient.Builder` and an embedding client
  from your `spring.ai.openai...` properties.

That's why in `AnswerGenerator.java` you can just ask for a `ChatClient.Builder` in the
constructor — you never created it; the starter's auto-configuration did.

> 💡 **Interview soundbite:** "Spring Boot starters give me a working `VectorStore` and
> `ChatClient` from configuration alone — auto-configuration wires the AI infrastructure so
> I focus on the retrieval and reasoning logic."

---

## 8. Tests without the whole app

**Look at:** `src/test/java/.../EligibilityEngineTest.java`

```java
class EligibilityEngineTest {
    private final EligibilityEngine engine = new EligibilityEngine(); // plain new!
    ...
}
```

Notice: in the test we DO call `new EligibilityEngine()` ourselves. Because the engine has
**no dependencies** (pure logic), we can test it as a plain Java object — no Spring, no
database, no API key. This is a direct payoff of good design: the safety-critical decision
logic is isolated and fast to test.

> 💡 This is the single best thing to show an interviewer: "My eligibility logic is pure and
> unit-tested in isolation, because deciding a citizen's benefit is safety-critical and must
> be verifiable."

---

## 9. How a single request flows through the whole app

Trace this path in the code (it's the best way to understand the project):

```
1. HTTP POST /api/navigate            → NavigatorController.navigate(...)
2. JSON → NavigateRequest (+ @Valid)  → web/NavigateRequest.java
3. request.toProfile()                → domain/CitizenProfile.java
4. navigatorService.navigate(...)     → service/NavigatorService.java   (orchestrator)
      ├─ retriever.retrieve(situation)      → rag/SchemeRetriever.java    (semantic search in pgvector)
      ├─ eligibilityEngine.evaluate(...)    → eligibility/EligibilityEngine.java  (deterministic rules)
      ├─ conflictDetector.detect(...)       → eligibility/ConflictDetector.java   (graph of exclusions)
      └─ answerGenerator.explain(...)       → rag/AnswerGenerator.java    (grounded LLM explanation)
5. NavigationResponse → JSON          → back to the citizen
```

If you can walk an interviewer through those 5 steps, you understand the project.

---

## 10. The architecture philosophy (your headline talking point)

The most important *idea* in GraminSahay is not a Spring feature — it's a design decision:

> **The LLM handles language. Deterministic rules make the decision.**

- `EligibilityEngine` (rules) decides ELIGIBLE / POSSIBLY / NOT / MISSING_INFO.
- `AnswerGenerator` (LLM) only *explains* that decision and cites the source — it is
  explicitly instructed it "cannot change the decision."

Why: a hallucinated "you are eligible" could send a poor citizen on a wasted trip and erode
trust. Rules are auditable; LLMs are not. This is your anti-hallucination story and the
thing that makes the project sound senior.

---

## 11. Suggested study order

1. `GraminSahayApplication.java` — the entry point (§3)
2. `domain/` package — the data shapes (records; plain Java, easy warm-up)
3. `eligibility/EligibilityEngine.java` — the core logic (pure Java, no Spring)
4. `src/test/.../EligibilityEngineTest.java` — see the logic proven (§8)
5. `rag/SchemeRetriever.java` + `rag/AnswerGenerator.java` — the RAG halves (§7)
6. `service/NavigatorService.java` — how it all connects (§9)
7. `web/NavigatorController.java` + `NavigateRequest.java` — the API edge (§4, §5)
8. `application.yml` + `pom.xml` — configuration & starters (§6, §7)

---

## 12. A 10-term Spring Boot glossary

| Term | Plain meaning |
|---|---|
| Bean | An object Spring creates and manages |
| Application context | Spring's registry of all beans |
| Dependency Injection | Spring passes a bean the other beans it needs |
| Component scan | Spring auto-finding your annotated classes |
| Stereotype annotation | `@Service`/`@Component`/`@Repository`/`@RestController` |
| Starter | A dependency bundle with auto-configuration |
| Auto-configuration | Spring creating beans for you based on classpath + properties |
| DTO | A simple object modelling a request/response |
| `@Value` | Inject a config value from `application.yml`/env |
| Embedded server | The web server (Tomcat) that ships inside the app |

Keep this table handy — these ten terms cover ~90% of what you'll be asked about Spring
Boot basics.
