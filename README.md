Implement Intent Classification Agent Before Concierge Agent

  Create a new Intent Guardrail Agent that classifies user input before routing to the concierge agent. This agent acts as a gatekeeper to ensure     
  conversations stay within supported scope.

  Requirements:

  1. Architecture:
    - Position this agent before the concierge agent in the workflow
    - Always call a tool (no direct responses)
    - Store intent classification in state for downstream agents
    - Reference implementation patterns from @/src/agent/agent/client_assist/core/agent.py and @/google/adk
  2. Intent Classifications (4 types):
    - greet - User greetings/pleasantries
    - investment_related - Questions within Investment GPT RAG scope [define scope below]
    - general_question - Generic questions answerable by the system
    - out_of_scope - Questions inappropriate for a bank representative content assistant
  3. State Management:
    - Initialize state with intent field
    - Agent updates state with classified intent
    - Downstream agents (concierge, Investment GPT) read intent from state
  4. Intent Scope Definitions:

  4. Investment Related:
    - [Insert Investment GPT capabilities/scope description here]

  Out of Scope:
    - Requests for actions/transactions (we only provide informational content)
    - Questions unrelated to banking/finance
    - Topics inappropriate for a bank's content-focused assistant

  Context:
  Our system wraps the Investment GPT RAG agent. This intent classifier ensures proper routing while maintaining the existing Investment GPT
  functionality. The agent validates scope before passing requests downstream.

  Key Point: This is a content delivery system (like "content GPTs") - information for consumption only, not transactional capabilities.
