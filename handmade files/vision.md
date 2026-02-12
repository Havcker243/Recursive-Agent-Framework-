- error handling
- new consortium and voting pair layer that considers node input and approaches, and defines what failiure and success means


# Memory System

All inputs:
User input (max focus)
base case agent context window
secret encoding and storage
support for different file types from pdfs to nix flakes
combine semantic vector encoding and tree-like graphs to create some kind of high-dimensional spatial relation memory system
need overwriting and correction of previous memories

What would be fucking sick: back-propogation based memory system to mimic how the human brain encodes memories, but only do this for non-critical things

different memory bucksts: one for credentials, one for instructions, one for purpose, one for actual long term memories, one for short term memories that have an expiration date when they move to long term memories, something like that
watches every context window in the system with different levels of effort put on each
separate tool calls from thinking tokens from conclusion tokens in these context windows and put different focus on each
focus on identifying aha moments, specific facts, and things that've been done
This way retrival can be more gauranteed because continuously running agents or agents assigned to similar problems can also have a position in this high dimensional memory space. Memories will look like tokens directionally attached to each other, like a cloud almost. My most basic idea of this is a chain-like degenerate tree which would simply encode strings of text, but what if text could be high-dimensional webs instead of strings, with ideas dynamically relating to each other?

Digital brain format options:

large neural network that remembers things via back propogation. Contradictions are corrected but remembered at the same time.

Dynamic spagetti soup. Nodes are tokens. Nodes have at most one child. 

dynamic semantic cloud soup: individual memories are a cloud of tokens in a high-dimensional semantically encoded space, maybe with significance and time as additional dimensions. All tokens are bidirenctionally connected and bidirenctionally weighted. from any point in the cloud, it could be asked "what other memories are related to this one?". This is like the connectionless but  When trees would excecute, they would leave behind 

Dynamic web: nodes are tokens. the nodes are connected to each other in a high-dimensional semantic space. Maybe time could be an additional dimension. 

connectionless: memories are simply stored as token clouds in a high-demensional semantic + time space. Traversing a single memory might look like following a trail of breadcrumbs, direction can kinda be felt out. Memories would all kinda point a similar direction in the time dimension. memory visualization could look like a 3d shadow of this entire brain, with time as a primary dimension that shows the virtual memory brain scanning forward through the time dimension.


Best design digital memory brain design fs:
Definite aspects:
Smallest unit of memory is a token.
Each token is recorded as a point in a high-dimensional semantically encoded space.
Unsure aspects:
Time as a dimension in the high-dimensional semantic space
Significance as a dimension in the high-dimensional semantic space

Outcomes:
Memories can be paralellized. For example, a list is no longer sequential, in can be some combination of sequential and paralell, have different significance and relation to other things and connotations, and reconverge later.

Problems:
I can think of how tree-like memories could easily be created: the memorizer LLM's output layer is used. Tokens relate to each other in definition and contextual meaning, and this is used to define their position in high-dimensional semantic space. One memory will stick together positionally, but the position of tokens related to each other is used to determine sequentialism (this makes a time dimension nescessary. Time is not nescessarily real-world time, could just be sequentialism). Tree memories can be created when the memorizer output LLM is trying to remember something. When the probability of selecting different tokens as the next token is within some threshhold. 


# Computer Use

Use nix flakes. Whenever a new workspace is created, the workspace can also be instanced across the tree. Here's an example:

Parent node task: Check whats been updated on my school LMS
Node has children:
Login agent: log into the site
memory system injects credentials and login process
grades agent: checks for new grades
New assignments agent: checks calendar for new assignments
One agent for each class, etc

All sibling agents will depend on the login agent. The login agent opens up a 


# Architecture
Main model will call RAF for anything that needs to be done, and RAF will respond later while the main model keeps up a conversation with the user.

If the user wants to make a change to a currently running raf tree, pause all currently running agents and have a summary of all work done back up the tree, then a new tree can be started that knows what's already been done and what needs to be undone.

