import json
from typing import Any, Dict, List

from raf.llm.adapter import ModelAdapter


class MockAdapter(ModelAdapter):
    def call_raw(self, task: str, payload: Dict[str, Any]) -> str:
        result = self._call_raw_inner(task, payload)
        # Estimate token usage: 1 token ≈ 4 chars (rough but consistent across all paths).
        payload_str = json.dumps(payload) if not isinstance(payload, str) else payload
        self._report_usage(len(payload_str) // 4, len(result) // 4)
        return result

    def _call_raw_inner(self, task: str, payload: Dict[str, Any]) -> str:
        def parse_hanoi(goal: str) -> Dict[str, Any]:
            text = goal.strip()
            if not text.startswith("HANOI(") or not text.endswith(")"):
                return {}
            inner = text[len("HANOI(") : -1]
            parts = [p.strip() for p in inner.split(",")]
            if len(parts) != 4:
                return {}
            try:
                n = int(parts[0])
                src = int(parts[1])
                dst = int(parts[2])
                aux = int(parts[3])
            except ValueError:
                return {}
            return {"n": n, "src": src, "dst": dst, "aux": aux}

        if task == "repair":
            original_task = payload.get("task")
            original_payload = payload.get("task_payload", {})
            return self.call_raw(original_task, original_payload)

        if task == "mode_decision":
            goal = payload.get("goal", "")
            depth = payload.get("depth", 0)
            hanoi = parse_hanoi(goal)
            if hanoi:
                mode = "recursive" if hanoi["n"] > 1 else "base"
                return json.dumps({"mode": mode, "reason": "Deterministic Hanoi mode."})
            # At depth >= 1, always go base (children are already focused sub-tasks)
            if depth >= 1:
                return json.dumps({"mode": "base", "reason": "Sufficient depth reached."})
            goal_lower = goal.lower()
            complex_kw = {
                "plan", "design", "build", "create", "develop", "research",
                "workout", "exercise", "fitness", "training",
                "essay", "write", "article", "report", "paper",
                "business", "startup", "product", "launch",
                "software", "app", "code", "implement", "feature",
            }
            if any(k in goal_lower for k in complex_kw):
                result = {"mode": "recursive", "reason": "Goal requires multiple distinct steps."}
            elif len(goal.split()) <= 6 or "simple" in goal_lower:
                result = {"mode": "base", "reason": "Goal appears simple enough to execute directly."}
            else:
                result = {"mode": "recursive", "reason": "Goal appears complex."}
            return json.dumps(result)

        if task == "plan":
            goal = payload.get("goal", "")
            hanoi = parse_hanoi(goal)
            if hanoi:
                n = hanoi["n"]
                src = hanoi["src"]
                dst = hanoi["dst"]
                aux = hanoi["aux"]
                if n <= 1:
                    children = []
                else:
                    children = [
                        {
                            "child_id": "child-1",
                            "goal": f"HANOI({n-1},{src},{aux},{dst})",
                            "depends_on": [],
                        },
                        {
                            "child_id": "child-2",
                            "goal": f"MOVE({n},{src},{dst})",
                            "depends_on": ["child-1"],
                        },
                        {
                            "child_id": "child-3",
                            "goal": f"HANOI({n-1},{aux},{dst},{src})",
                            "depends_on": ["child-2"],
                        },
                    ]
                return json.dumps({"children": children, "rationale": "Hanoi recursive decomposition."})
            goal_lower = goal.lower()
            fitness_kw = {"fitness", "workout", "exercise", "training", "gym", "strength", "cardio", "muscle"}
            essay_kw = {"essay", "write", "article", "research", "report", "paper", "blog"}
            business_kw = {"business", "startup", "company", "product", "launch", "venture"}
            software_kw = {"software", "build", "develop", "app", "code", "feature", "implement", "api"}

            if any(k in goal_lower for k in fitness_kw):
                children = [
                    {"child_id": "child-1", "goal": f"Define training goals and current fitness baseline for: {goal}", "depends_on": []},
                    {"child_id": "child-2", "goal": f"Select exercise types and weekly structure for: {goal}", "depends_on": ["child-1"]},
                    {"child_id": "child-3", "goal": f"Design progressive overload schedule for: {goal}", "depends_on": ["child-2"]},
                    {"child_id": "child-4", "goal": f"Plan nutrition and recovery strategy to support: {goal}", "depends_on": ["child-2"]},
                ]
                rationale = "Decomposed into baseline assessment, exercise selection, progression, and nutrition."
            elif any(k in goal_lower for k in essay_kw):
                children = [
                    {"child_id": "child-1", "goal": f"Identify thesis and key arguments for: {goal}", "depends_on": []},
                    {"child_id": "child-2", "goal": f"Research and gather supporting evidence for: {goal}", "depends_on": ["child-1"]},
                    {"child_id": "child-3", "goal": f"Draft introduction and body sections for: {goal}", "depends_on": ["child-2"]},
                    {"child_id": "child-4", "goal": f"Write conclusion and edit for coherence for: {goal}", "depends_on": ["child-3"]},
                ]
                rationale = "Decomposed into thesis, research, drafting, and editing phases."
            elif any(k in goal_lower for k in business_kw):
                children = [
                    {"child_id": "child-1", "goal": f"Define target market and problem statement for: {goal}", "depends_on": []},
                    {"child_id": "child-2", "goal": f"Analyse competitive landscape for: {goal}", "depends_on": ["child-1"]},
                    {"child_id": "child-3", "goal": f"Outline product or service offering for: {goal}", "depends_on": ["child-1"]},
                    {"child_id": "child-4", "goal": f"Create revenue model and financial projections for: {goal}", "depends_on": ["child-2", "child-3"]},
                ]
                rationale = "Decomposed into market definition, competition, product, and financials."
            elif any(k in goal_lower for k in software_kw):
                children = [
                    {"child_id": "child-1", "goal": f"Define requirements and acceptance criteria for: {goal}", "depends_on": []},
                    {"child_id": "child-2", "goal": f"Design system architecture and data model for: {goal}", "depends_on": ["child-1"]},
                    {"child_id": "child-3", "goal": f"Implement core functionality for: {goal}", "depends_on": ["child-2"]},
                    {"child_id": "child-4", "goal": f"Write tests and validate against requirements for: {goal}", "depends_on": ["child-3"]},
                ]
                rationale = "Decomposed into requirements, design, implementation, and testing."
            else:
                children = [
                    {"child_id": "child-1", "goal": f"Analyse scope and identify key deliverables for: {goal}", "depends_on": []},
                    {"child_id": "child-2", "goal": f"Execute primary tasks for: {goal}", "depends_on": ["child-1"]},
                    {"child_id": "child-3", "goal": f"Review, integrate, and finalise output for: {goal}", "depends_on": ["child-2"]},
                ]
                rationale = "Generic decomposition into analysis, execution, and review."
            return json.dumps({"children": children, "rationale": rationale})

        if task == "vote":
            options = payload.get("options", [])
            if not options:
                return json.dumps({"winner_id": "", "ranked": [], "confidence": 0.0})
            ranked = []
            for i, option in enumerate(options):
                ranked.append({"option_id": option["option_id"], "score": 10 - i, "reason": "OK"})
            return json.dumps({"winner_id": options[0]["option_id"], "ranked": ranked, "confidence": 0.85})

        if task == "base_execute":
            goal = payload.get("goal", "")
            # Spec repair nodes have goals shaped like "PRIMARY OBJECTIVE...\n\nPATCH..."
            # Extract the current output and return it unchanged — the mock has no
            # real repair capability, so pass-through is the correct behaviour.
            if "PRIMARY OBJECTIVE" in goal and "PATCH" in goal:
                current_output_marker = "Current output:\n"
                if current_output_marker in goal:
                    current_output = goal.split(current_output_marker, 1)[1].strip()
                else:
                    # Pull the actual goal from the PRIMARY OBJECTIVE line
                    first_line = goal.split("\n", 1)[0]
                    current_output = first_line.replace("PRIMARY OBJECTIVE (never deviate from this):", "").strip()
                return json.dumps({
                    "output": current_output,
                    "key_points": ["repair pass-through"],
                    "scope_notes": ["Mock: returned existing output unchanged."],
                })
            if goal.startswith("MOVE(") and goal.endswith(")"):
                inner = goal[len("MOVE(") : -1]
                parts = [p.strip() for p in inner.split(",")]
                if len(parts) == 3:
                    return json.dumps(
                        {
                            "output": f"Move disk {parts[0]} from {parts[1]} to {parts[2]}",
                            "key_points": [f"move {parts[0]}"],
                            "scope_notes": ["Deterministic move."],
                        }
                    )
            if goal.startswith("HANOI(") and goal.endswith(")"):
                hanoi = parse_hanoi(goal)
                if hanoi and hanoi["n"] == 1:
                    return json.dumps(
                        {
                            "output": f"Move disk 1 from {hanoi['src']} to {hanoi['dst']}",
                            "key_points": ["move 1"],
                            "scope_notes": ["Base Hanoi move."],
                        }
                    )
            goal_lower = goal.lower()
            fitness_kw = {"fitness", "workout", "exercise", "training", "gym", "strength", "cardio", "muscle"}
            essay_kw = {"essay", "write", "article", "research", "report", "paper", "blog"}
            business_kw = {"business", "startup", "company", "product", "launch", "venture"}
            software_kw = {"software", "build", "develop", "app", "code", "feature", "implement", "api"}

            if any(k in goal_lower for k in fitness_kw):
                output = f"[Mock] Completed: {goal}. Recommended 4-day split: push/pull/legs/full-body. Progressive overload at 5% per week."
                key_points = ["4-day training split", "progressive overload", "deload every 4th week"]
            elif any(k in goal_lower for k in essay_kw):
                output = f"[Mock] Completed: {goal}. Drafted structured argument with introduction, three supporting paragraphs, and conclusion."
                key_points = ["clear thesis", "three supporting arguments", "conclusion with takeaway"]
            elif any(k in goal_lower for k in business_kw):
                output = f"[Mock] Completed: {goal}. Identified target segment, competitive advantages, and 18-month revenue roadmap."
                key_points = ["target segment defined", "competitive moat identified", "revenue model outlined"]
            elif any(k in goal_lower for k in software_kw):
                output = f"[Mock] Completed: {goal}. Implemented feature with unit tests passing and PR ready for review."
                key_points = ["requirements met", "unit tests written", "code reviewed"]
            else:
                output = f"[Mock] Completed: {goal}."
                key_points = ["task completed", "output verified"]
            return json.dumps({
                "output": output,
                "key_points": key_points,
                "scope_notes": ["Stayed on goal scope."],
            })

        if task == "merge":
            goal = payload.get("goal", "")
            child_outputs = payload.get("child_outputs", [])
            child_texts = [
                item.get("output", json.dumps(item)) if isinstance(item, dict) else str(item)
                for item in child_outputs
            ]
            summary = "; ".join(child_texts)[:200]
            if goal.startswith("HANOI("):
                moves = "\n".join(child_texts)
                return json.dumps(
                    {
                        "output": moves,
                        "key_points": ["Merged Hanoi moves"],
                        "scope_notes": ["Merged only child outputs."],
                    }
                )
            return json.dumps(
                {
                    "output": f"Merged result for goal: {goal}. Summary: {summary}",
                    "key_points": ["Merged A", "Merged B"],
                    "scope_notes": ["Merged only child outputs."],
                }
            )

        if task == "analysis":
            return json.dumps({"approved": True, "confidence": 0.85, "reason": "Looks acceptable."})

        if task == "clarify":
            goal = payload.get("goal", "")
            g = goal.lower()
            # Mock adapter does not simulate LLM intelligence for question generation.
            # It only tests the clarification flow: ask once if the goal is very short
            # and no prior user context has been provided.
            has_prior_context = "user answer:" in g
            is_deterministic = goal.startswith("HANOI(") or goal.startswith("MOVE(")
            is_underspecified = len(goal.split()) < 8
            if not has_prior_context and not is_deterministic and is_underspecified:
                return json.dumps({"questions": ["Could you provide more details — what specific outcome, constraints, or context should be kept in mind?"]})
            return json.dumps({"questions": []})

        if task == "refine_context":
            child_id = payload.get("child_id", "child-1")
            goal = payload.get("goal", "")
            depends_on = payload.get("depends_on", [])
            return json.dumps({"child_id": child_id, "goal": goal, "depends_on": depends_on})

        if task == "scope_check":
            # Mock always approves — real LLMs do the actual semantic check
            return json.dumps({"on_topic": True, "reason": "Mock: scope check passed."})

        return json.dumps({"error": "Unknown task"})
