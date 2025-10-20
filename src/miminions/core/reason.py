# @title Define ReasoningLLM
from typing import List, Dict, Any
import time

from src.miminions.core.base import BaseLLM



class ReasoningLLM:
    """Demonstrates reasoning framework - multiple orchestrated calls"""

    def __init__(self, base_llm: BaseLLM):
        self.base_llm = base_llm
        self.conversation_history = []

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Step 1: Analyze the type of query and create reasoning plan"""
        analysis_prompt = f"""
        Analyze this query and determine the best approach to answer it comprehensively:
        Query: "{query}"

        Respond with:
        1. Query type (factual, process, comparison, etc.)
        2. Key components to address
        3. Suggested breakdown steps

        Keep response concise and structured.
        """

        print("🔧 ReasoningLLM: Step 1 - Analyzing query...")
        response = self.base_llm.generate(analysis_prompt)
        return {"analysis": response["content"], "tokens": response["tokens_used"]}

    def decompose_problem(self, query: str, analysis: str) -> List[str]:
        """Step 2: Break down into specific sub-questions"""
        decomposition_prompt = f"""
        Based on this analysis: {analysis}

        Break down the query "{query}" into 3-4 specific sub-questions that, when answered together,
        will provide a comprehensive response. List only the questions, one per line.
        """

        print("🔧 ReasoningLLM: Step 2 - Decomposing problem...")
        response = self.base_llm.generate(decomposition_prompt)

        # Extract questions from response
        questions = [q.strip() for q in response['content'].split('\n') if q.strip() and '?' in q]
        return questions[:4]  # Limit to 4 questions

    def answer_sub_question(self, question: str) -> str:
        """Step 3: Answer each sub-question specifically"""
        focused_prompt = f"""
        Answer this specific question with precise, technical details:
        {question}

        Provide a clear, factual answer focusing only on this aspect.
        """

        print(f"🔧 ReasoningLLM: Step 3 - Answering: {question[:50]}...")
        response = self.base_llm.generate(focused_prompt)
        return response["content"]

    def verify_response(self, question: str, answer: str) -> Dict[str, Any]:
        """Step 4: Verify accuracy and completeness"""
        verification_prompt = f"""
        Question: {question}
        Answer: {answer}

        Evaluate this answer on a scale of 1-10 for:
        1. Accuracy
        2. Completeness
        3. Clarity

        Respond with just three numbers and any critical missing information.
        """

        print("🔧 ReasoningLLM: Step 4 - Verifying response...")
        response = self.base_llm.generate(verification_prompt)
        return {"verification": response["content"]}

    def synthesize_final_response(self, query: str, qa_pairs: List[tuple]) -> str:
        """Step 5: Combine all verified answers into structured response"""
        synthesis_prompt = f"""
        Original question: {query}

        Sub-questions and answers with verifications:
        {chr(10).join([
            f"Q: {qa['question']}\nA: {qa['answer']}\nVerification: {qa['verification']}\n"
            for qa in qa_pairs
        ])}

        Synthesize these into a well-structured, comprehensive answer to the original question.
        Use clear steps/sections and ensure logical flow.
        """

        print("🔧 ReasoningLLM: Step 5 - Synthesizing final response...")
        response = self.base_llm.generate(synthesis_prompt)
        return response["content"]

    def reason(self, query: str) -> Dict[str, Any]:
        """Main reasoning orchestration method"""
        print(f"\n🔧 ReasoningLLM: Processing '{query}'")
        start_time = time.time()

        # Step 1: Analyze query
        analysis = self.analyze_query(query)

        # Step 2: Decompose into sub-questions
        sub_questions = self.decompose_problem(query, analysis['analysis'])

        # Step 3 & 4: Answer and verify each sub-question
        qa_pairs = []
        total_tokens = analysis['tokens']

        for question in sub_questions:
            answer = self.answer_sub_question(question)
            verification = self.verify_response(question, answer)
            qa_pairs.append({
                "question": question,
                "answer": answer,
                "verification": verification["verification"]
            })
            total_tokens += 100  # Approximate token usage

        # Step 5: Synthesize final response
        final_response = self.synthesize_final_response(query, qa_pairs)

        end_time = time.time()

        return {
            "response": final_response,
            "reasoning_steps": {
                "analysis": analysis['analysis'],
                "sub_questions": sub_questions,
                "qa_pairs": qa_pairs
            },
            "total_tokens": total_tokens,
            "processing_time": end_time - start_time
        }