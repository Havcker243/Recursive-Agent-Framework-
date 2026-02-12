<!-- 
  AI AGENTS: This file contains ONLY direct requests from Bennett (the human).
  DO NOT add AI-generated ideas, suggestions, or interpretations to this file.
  Only Bennett's exact words and requirements belong here.
  If you want to add your own ideas, use plan.md or another file.
-->

# High-Level Plan — RAF Architecture Option Visualizer

## What This Is

A color-coded panel where I can visualize design decisions, turning different things on and off.

## Data Storage

The data storage for each of the segments I can turn on and off should be stored in mermaid graphs, with the core mermaid graph having nodes in it that are "options" — a place where elements that there are a toggle for would appear or not.

## Tech Stack

- React with TypeScript and Tailwind
- Uses the frontend design skill already in the raf-architecture-visualizer folder
- D3.js for the physics-enabled tree graph
- The raf-architecture-visualizer folder should be the root folder for the React app

## Layout

- Config panel off to the left
- Main D3.js view taking up most of the screen on the right
- Pan and zoom support
- Hover over nodes to see more information

## Controls

- Sliders for the number of agents in each cluster
- For now, the only toggle is the extra context processing agent jury and consortium that's the difference between the original pseudocode and v2

## Visualization

- Color-coded and physics-enabled tree graph of execution using D3.js
- This will essentially be a dynamic visualizer of the pseudocode so I can visually see the different ideas I'm considering
- A toggle between viewing the resulting mermaid graph of the settings, and the physics-enabled and more feature-rich D3.js visualization

## Physics Constraints

- A constraint on the physics that keeps the base case and recursive case branches parallel to each other
