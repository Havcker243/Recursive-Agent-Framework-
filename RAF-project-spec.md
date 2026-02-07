# RAF: A generalized agent orchestration framework for any horizon-length agentic task

A framework that implements Agent Communication Protocol to provide an agent that 

## Design dogmas

- **Signal to noise ratio optimization:** This isn't just the main reason why I'm building this system, it's a core ideology that applies to every part of it. Each member of the swarm should handle as little noise and as much signal as possible.

- **Recursion:** This system should break down tasks into minimum-viable context windows. No context window should be used for something that would be beneficial to be split up.

- **Multi-Model:** This system should improve the more models it has access to. The more diversity in selection of models, the more diversity of opinion in descision making, the more the system can dedicate the appropriate compute to each task, the more the system can take advantage of a mixture-of-experts approach, etc.

- **Decision aggregation:** Each decision made by the system should be voted on by a congress of agents. For example, when a task is presented to a stem agent, it should spawn a consortium of agents to come up with all the possible ways of breaking down the task to the next batch of RLMs. 

- **Strong enforcement of output format and typing:** This allows a much logic as possible to be hard coded, and makes it easy to throw out bad responses because an LLM not following output format is a great indicator that it outputted a bad response.

## Definitions

- **RLM:** Recursive language model, the primary technology behind this system. A language model that breaks down its task into smaller parts, or excecutes the task if it shouldn't be broken down any further. Each RLM starts as a stem agent. 

- **Stem agent:** These agents are like stem cells in biology, with a wide context window and access to all available tools, but they don't excecute anything and are only for planning. They are used at each step of an RLM for context window optimization and to orchestrate a recursive step. The life cycle of a stem agent consists of calling a consortium on the task spec then deploying either a base-case excecutor agent or the next set of RLMs. (should probably be hard-coded and not actually involve an llm, stem agent might be a misnomer.)

- **Base-case agent:** This is an agent that is given a very specific smallest possible task spec, set of tools, and output formatting. Returns either a promise of success or an error message.

- **Consortium:** A team of agents (ideally consisting of a selection of different models depending on how many are available to the system) that come up with all possible solutions to a problem. For example, when given the current task from a stem agent, they would all independently come up with all the different ways of breaking down a task into a set of more than one next recursive calls. In some cases, the next set of recursive calls doesn't have to be completely synchronous and excecuted in a specific order or completely asynchronous, it can instead use a hybrid model where some steps are allowed require the output of a sibling step and will therefore wait for it to return a result and/or some additional context before proceeding. Next, another smaller team of agents aggregates all the proposals into a single list via a union, with duplicates being intelligently merged to include all aspects of each version of the duplicate. If there are any conflicts in a duplicate, then it isn't a duplicate and shouldn't be merged. Next, a congressional vote is called on which aggregation is the most accurate, with the context windows of all voters including the current step's original task spec and all of the proposed aggregations. That congress will then return which list of options is the best, then a second fresh congressional vote will be called on which option out of that list is the best, with a "base-case" option appended to that list of choices.

- **Congress:** A temporary ensemble of heterogeneous agents that performs decision-making as probabilistic inference. Each member independently evaluates the full choice set and returns a complete ranking under a fixed rubric. Rankings are aggregated using a reliability-weighted Plackett–Luce model to produce a posterior distribution over option quality. Congress outputs (a) the selected action for control flow and (b) a decision record containing the full aggregated ranking, posterior scores, and uncertainty (b is only logged and not passed back to the caller of the congress, only a is returned). This decision record is used for auditing, backtracking, and fallbacks, while the selected action is used to advance execution. Agent reliabilities are updated online from downstream validation, and highly correlated rankings are downweighted to preserve epistemic diversity. MVP will be non-self-improving, and just use a fixed consortium of diverse agents. 

- **Entry point agent:** The highest available intelligence model of the system. It's called by a user or other AI system that wants to call this system over ACP, and parses the base task.