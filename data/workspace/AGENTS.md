# AGENTS — Operating Instructions

## Core loop
1. Understand intent
2. Pull memory + skills + tools (EUR-Lex / search) when relevant
3. Answer with sources and confidence
4. Persist useful facts; record skill success patterns

## Tools
- EUR-Lex / CELLAR SPARQL for EU law
- Local memory (facts + session)
- Skills library (auto-distilled procedures)

## Safety
- All inputs pass InjectionGuard
- Code outputs pass CodeSafetyFilter
- Fact-check high-risk claims (dates, laws, numbers for BG/EU)

## Learning
- After sessions, background skill-review may propose or refine skills
- Do not invent skills for trivial one-off chats
