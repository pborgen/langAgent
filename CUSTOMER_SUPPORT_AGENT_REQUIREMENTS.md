# Customer Support Agent for Small Businesses

## 1. Product Goal
Build a customer support agent SaaS for small businesses with strong monetization potential.

## 2. What It Does
Businesses upload FAQs, product docs, order history, and related support content.  
The agent must:

- Answer customer questions 24/7 via website chat or email
- Look up order status using custom tools
- Book appointments using a Google Calendar tool
- Escalate conversations to a human with full context

## 3. Key LangChain/LangGraph Requirements

- RAG over uploaded business documents
- LangGraph conversation state and routing:
  - Simple query -> answer automatically
  - Complex/risky query -> escalate to human
- Tool calling + memory across sessions
- Human-in-the-loop support (pause for approval before escalation/actions when needed)

## 4. Tech Stack Requirements

- LangChain + LangGraph
- Vector DB: Pinecone or Supabase (pgvector)
- Backend/API: FastAPI or Next.js
- Payments: Stripe

## 5. Monetization Requirements

- SaaS pricing model: $29-$99/month per business (unlimited chats)
- Optional embedded widget for Shopify/Wix; charge per installation
- White-label offering for agencies to resell
- Long-term target inspired by similar products: $5k-$20k MRR

## 6. Market Value / Positioning

- Small businesses often want a lower-cost alternative to Zendesk ($50-$200/month range)
- Strong value proposition: a ~$29/month support agent trained on the business's own product/docs
- Portfolio and freelance value:
  - Positioning example: \"I’ll build your custom support agent in 1 week\"
