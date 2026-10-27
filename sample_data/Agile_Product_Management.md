# Product Management Study Notes: Agile & Scrum Framework

## Chapter 1: Introduction to Agile Methodology
Agile is an iterative approach to project management and software development that helps teams deliver value to their customers faster and with fewer headaches. Instead of betting everything on a "big bang" launch, an agile team delivers work in small, but consumable, increments.

### The 4 Agile Values:
1. **Individuals and interactions** over processes and tools
2. **Working software** over comprehensive documentation
3. **Customer collaboration** over contract negotiation
4. **Responding to change** over following a plan

---

## Chapter 2: The Scrum Framework

### What is Scrum?
Scrum is an agile framework that helps teams work together. It describes a set of meetings, tools, and roles for efficient project delivery.

### Scrum Roles:
- **Product Owner (PO):** Defines the product vision, manages the Product Backlog, and prioritizes features based on business value and user needs.
- **Scrum Master:** A servant-leader who coaches the team, facilitates Scrum ceremonies, and removes impediments (blockers) that hinder the team.
- **Development Team:** A cross-functional, self-organizing group of specialists (engineers, designers, QA) who execute the work to produce a shippable increment.

### What is a Sprint?
A **Sprint** is a fixed period (timebox) of typically 1 to 4 weeks during which a scrum team works to complete a planned set of tasks and produce a potentially shippable product increment.
- **Key Characteristics of a Sprint:**
  - Sprints have consistent durations throughout a development effort.
  - A new Sprint starts immediately after the conclusion of the previous Sprint.
  - During the Sprint, no changes are made that would endanger the Sprint Goal.
  - Quality goals do not decrease.
  - Scope may be clarified and re-negotiated between the Product Owner and the Development Team as more is learned.

---

## Chapter 3: Scrum Ceremonies (Events)

### 1. Sprint Planning
The team determines the Sprint Goal and selects items from the top of the Product Backlog to include in the Sprint Backlog.

### 2. Daily Scrum (Standup)
A 15-minute daily timeboxed meeting for the team to synchronize activities. Each member answers:
1. What did I accomplish yesterday?
2. What will I work on today?
3. Are there any impediments or blockers in my way?

### 3. Sprint Review
Held at the end of the Sprint to inspect the Increment and adapt the Product Backlog if needed. The team demonstrates the working software to stakeholders and receives feedback.

### 4. Sprint Retrospective
A dedicated opportunity for the Scrum Team to inspect itself and create a plan for improvements to be enacted during the next Sprint. Focuses on people, relationships, processes, and tools.

---

## Chapter 4: Agile Artifacts and Estimation

### Product Backlog vs. Sprint Backlog
- **Product Backlog:** An emergent, ordered list of what is needed to improve the product. Single source of requirements for any changes.
- **Sprint Backlog:** A set of Product Backlog items selected for the Sprint, plus a plan for delivering the Increment and realizing the Sprint Goal.

### User Stories & The INVEST Criteria
A User Story is a concise description of a feature told from the perspective of the end user:
- *Template:* "As a [type of user], I want [an action] so that [a benefit/value]."
- **INVEST Criteria:**
  - **I**ndependent: Can be developed separately without tight coupling.
  - **N**egotiable: Open to discussion and refinement.
  - **V**aluable: Delivers clear value to users or stakeholders.
  - **E**stimable: Size and complexity can be reasonably estimated.
  - **S**mall: Can be completed within a single sprint.
  - **T**estable: Clear acceptance criteria allow QA verification.

### Estimation & Velocity
- **Story Points:** A relative unit of measure used by agile teams to estimate the overall effort required to fully implement a user story (taking into account complexity, uncertainty, and volume of work).
- **Velocity:** The average number of story points completed by a team during a sprint. Used for capacity planning in future sprints.
- **Burndown Chart:** A graphical representation of work left to do versus time. Helps track whether the team will achieve the sprint goal on schedule.

---

## Chapter 5: Scrum vs. Kanban

| Feature | Scrum | Kanban |
| :--- | :--- | :--- |
| **Cadence** | Fixed timeboxed sprints (1–4 weeks) | Continuous flow |
| **Roles** | Product Owner, Scrum Master, Dev Team | No prescribed roles |
| **Metrics** | Velocity, Sprint Burndown | Lead Time, Cycle Time, WIP limits |
| **Changes** | No mid-sprint changes to sprint goal | Changes can be introduced at any time |
