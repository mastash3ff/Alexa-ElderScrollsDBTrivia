"""Tests for Elder Scrolls Dark Brotherhood Trivia Alexa skill."""
from unittest.mock import MagicMock
from ask_sdk_model import LaunchRequest, IntentRequest, Intent, Slot

import lambda_function as lf
from data import QUESTIONS

GAME_LENGTH = lf.GAME_LENGTH  # 5
ANSWER_COUNT = lf.ANSWER_COUNT  # 4


def make_hi(request, session_attrs=None):
    hi = MagicMock()
    hi.request_envelope.request = request
    hi.attributes_manager.session_attributes = {} if session_attrs is None else dict(session_attrs)
    rb = MagicMock()
    for m in ("speak", "ask", "set_card", "set_should_end_session"):
        getattr(rb, m).return_value = rb
    hi.response_builder = rb
    return hi


def make_intent(name, slots=None):
    slot_objs = {k: Slot(name=k, value=str(v)) for k, v in (slots or {}).items()}
    return IntentRequest(intent=Intent(name=name, slots=slot_objs))


def game_attrs(question_index=0, score=0, correct_index=2):
    """Return session attributes for an in-progress game."""
    return {
        "questions": list(range(GAME_LENGTH)),
        "current_question_index": question_index,
        "correct_answer_index": correct_index,  # 1-based
        "correct_answer_text": "Correct Answer Text",
        "score": score,
        "speech_output": "Question text",
        "reprompt_text": "Question text",
    }


class TestLaunchRequest:
    def test_can_handle(self):
        assert lf.LaunchRequestHandler().can_handle(make_hi(LaunchRequest()))

    def test_starts_game_sets_session_attrs(self):
        hi = make_hi(LaunchRequest())
        lf.LaunchRequestHandler().handle(hi)
        attrs = hi.attributes_manager.session_attributes
        assert "questions" in attrs
        assert len(attrs["questions"]) == GAME_LENGTH
        assert attrs["score"] == 0
        assert attrs["current_question_index"] == 0

    def test_speaks_intro(self):
        hi = make_hi(LaunchRequest())
        lf.LaunchRequestHandler().handle(hi)
        speech = hi.response_builder.speak.call_args[0][0]
        assert "Elder Scrolls" in speech
        assert "Question 1" in speech

    def test_keeps_session_open(self):
        hi = make_hi(LaunchRequest())
        lf.LaunchRequestHandler().handle(hi)
        hi.response_builder.ask.assert_called_once()
        hi.response_builder.set_should_end_session.assert_not_called()


class TestAnswerIntent:
    def test_can_handle(self):
        assert lf.AnswerIntentHandler().can_handle(
            make_hi(make_intent("AnswerIntent"), session_attrs=game_attrs())
        )

    def test_correct_answer_increments_score(self):
        attrs = game_attrs(correct_index=2)
        hi = make_hi(make_intent("AnswerIntent", slots={"Answer": "2"}), session_attrs=attrs)
        lf.AnswerIntentHandler().handle(hi)
        assert hi.attributes_manager.session_attributes["score"] == 1

    def test_wrong_answer_does_not_increment_score(self):
        attrs = game_attrs(correct_index=2)
        hi = make_hi(make_intent("AnswerIntent", slots={"Answer": "3"}), session_attrs=attrs)
        lf.AnswerIntentHandler().handle(hi)
        assert hi.attributes_manager.session_attributes["score"] == 0

    def test_wrong_answer_reveals_correct(self):
        attrs = game_attrs(correct_index=2)
        hi = make_hi(make_intent("AnswerIntent", slots={"Answer": "1"}), session_attrs=attrs)
        lf.AnswerIntentHandler().handle(hi)
        speech = hi.response_builder.speak.call_args[0][0]
        assert "wrong" in speech.lower() or "correct answer" in speech.lower()

    def test_no_game_in_progress_prompts_start(self):
        hi = make_hi(make_intent("AnswerIntent", slots={"Answer": "1"}))
        lf.AnswerIntentHandler().handle(hi)
        speech = hi.response_builder.speak.call_args[0][0]
        assert "no game" in speech.lower() or "start" in speech.lower()

    def test_invalid_answer_reprompts(self):
        attrs = game_attrs()
        hi = make_hi(make_intent("AnswerIntent", slots={"Answer": "99"}), session_attrs=attrs)
        lf.AnswerIntentHandler().handle(hi)
        speech = hi.response_builder.speak.call_args[0][0]
        assert "between 1 and" in speech

    def test_last_question_ends_game(self):
        attrs = game_attrs(question_index=GAME_LENGTH - 1, score=3, correct_index=1)
        hi = make_hi(make_intent("AnswerIntent", slots={"Answer": "1"}), session_attrs=attrs)
        lf.AnswerIntentHandler().handle(hi)
        speech = hi.response_builder.speak.call_args[0][0]
        assert "Thank you for playing" in speech
        hi.response_builder.set_should_end_session.assert_called_once_with(True)


class TestDontKnowIntent:
    def test_can_handle(self):
        assert lf.DontKnowIntentHandler().can_handle(make_hi(make_intent("DontKnowIntent")))

    def test_reveals_correct_answer(self):
        attrs = game_attrs(correct_index=3)
        hi = make_hi(make_intent("DontKnowIntent"), session_attrs=attrs)
        lf.DontKnowIntentHandler().handle(hi)
        speech = hi.response_builder.speak.call_args[0][0]
        assert "correct answer" in speech.lower() or "3" in speech

    def test_no_game_starts_new_game(self):
        hi = make_hi(make_intent("DontKnowIntent"))
        lf.DontKnowIntentHandler().handle(hi)
        assert "questions" in hi.attributes_manager.session_attributes


class TestStartOverIntent:
    def test_can_handle(self):
        assert lf.StartOverIntentHandler().can_handle(
            make_hi(make_intent("AMAZON.StartOverIntent"))
        )

    def test_resets_score(self):
        attrs = game_attrs(score=3, question_index=2)
        hi = make_hi(make_intent("AMAZON.StartOverIntent"), session_attrs=attrs)
        lf.StartOverIntentHandler().handle(hi)
        assert hi.attributes_manager.session_attributes["score"] == 0
        assert hi.attributes_manager.session_attributes["current_question_index"] == 0


class TestQuestionBank:
    def test_has_enough_questions(self):
        assert len(QUESTIONS) >= GAME_LENGTH

    def test_each_question_has_correct_format(self):
        for q in QUESTIONS:
            assert len(q) == 1
            answers = list(q.values())[0]
            assert len(answers) >= ANSWER_COUNT
