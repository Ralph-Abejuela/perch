# Perch

Self-hostable live chat widget. A business (Tenant) embeds a Widget on their website; their Agents answer Visitor conversations in real time from a dashboard.

## Language

**Tenant**:
A business that signs up for Perch. One deployment of Perch serves many Tenants; all data belongs to exactly one Tenant.
_Avoid_: customer, account, workspace, organization

**Site**:
A website a Tenant registers with Perch. A Tenant may have several Sites; each Site has its own Widget key. Plan limits are counted in Sites.
_Avoid_: domain, project, property

**Agent**:
A person belonging to a Tenant who signs in to the dashboard and replies to Conversations.
_Avoid_: user, operator, staff

**Visitor**:
An anonymous person chatting through a Widget on a Site. Identified only by an auto-generated Visitor ID unless they supply name/email via the identify API.
_Avoid_: guest, customer, end-user

**Widget**:
The small embeddable script + chat bubble a Tenant installs on a Site. The only Perch surface a Visitor touches.
_Avoid_: snippet, embed, chat box

**Identify**:
The act of attaching a name and/or email to a Visitor, done by the Site's own code calling the Widget's public JS API.
_Avoid_: login (Visitors never log in), profile

**Conversation**:
One Visitor's chat thread on one Site. Has a status (open, closed) and belongs to exactly one Site.
_Avoid_: session, ticket, thread

**Message**:
A single utterance inside a Conversation, sent by either the Visitor or an Agent.
_Avoid_: reply, comment, chat

**Presence**:
The realtime online/offline state of an Agent (visible to Visitors and other Agents) and typing state within a Conversation.

**Offline capture**:
When no Agent of the Site is online, the Widget collects the Visitor's email and message instead of starting a live Conversation.
_Avoid_: fallback form, contact form

**Plan**:
A Tenant's service tier (e.g. Free, Pro) that caps Sites and Agents. Enforced in the application; billing integration is out of scope for v1.
