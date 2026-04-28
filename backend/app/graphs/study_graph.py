from __future__ import annotations

from dataclasses import dataclass

from langgraph.graph import END, StateGraph


@dataclass
class StudyState:
    question: str
    answer: str = ""


def build_study_graph(answer_fn):
    graph = StateGraph(StudyState)

    def retrieve_and_answer(state: StudyState):
        answer, _sources = answer_fn(state.question)
        return {"answer": answer}

    graph.add_node("answer", retrieve_and_answer)
    graph.set_entry_point("answer")
    graph.add_edge("answer", END)
    return graph.compile()

