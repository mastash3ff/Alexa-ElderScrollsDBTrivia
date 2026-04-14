import random

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_model.ui import SimpleCard

from data import QUESTIONS

GAME_LENGTH = 5
ANSWER_COUNT = 4
CARD_TITLE = "Elder Scrolls Dark Brotherhood Trivia"

sb = SkillBuilder()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pick_game_questions() -> list[int]:
    """Return GAME_LENGTH unique random indices into QUESTIONS."""
    indices = list(range(len(QUESTIONS)))
    random.shuffle(indices)
    return indices[:GAME_LENGTH]


def _build_question_speech(question_number: int, question_index: int, correct_slot: int) -> tuple[str, str]:
    """
    Build the spoken question string and return (speech, correct_answer_text).

    correct_slot  – 0-based position where the correct answer will be placed
                    among the ANSWER_COUNT choices read aloud.

    Returns (reprompt_text, correct_answer_text) where reprompt_text is the
    full "Question N. … 1. … 2. … 3. … 4." string.
    """
    entry = QUESTIONS[question_index]
    question_text = list(entry.keys())[0]
    answers_master = list(entry.values())[0]  # index 0 is always the correct answer

    # Shuffle the wrong answers (indices 1..end), then take ANSWER_COUNT total
    wrong = answers_master[1:]
    random.shuffle(wrong)
    pool = [answers_master[0]] + wrong  # correct first, then shuffled wrongs
    choices = pool[:ANSWER_COUNT]       # exactly ANSWER_COUNT choices

    # Swap the correct answer into the target slot
    choices[0], choices[correct_slot] = choices[correct_slot], choices[0]

    reprompt = f"Question {question_number}. {question_text} "
    for i, choice in enumerate(choices, start=1):
        reprompt += f"{i}. {choice}. "

    return reprompt, answers_master[0]


def _start_game(handler_input: HandlerInput) -> Response:
    """Shared logic for LaunchRequest and StartOverIntent."""
    game_questions = _pick_game_questions()
    correct_slot = random.randint(0, ANSWER_COUNT - 1)  # 0-based
    reprompt_text, correct_answer_text = _build_question_speech(1, game_questions[0], correct_slot)

    intro = (
        f"Elder Scrolls Dark Brotherhood Trivia. "
        f"I will ask you {GAME_LENGTH} questions, try to get as many right as you can. "
        f"Just say the number of the answer. Let's begin. "
    )
    speech_output = intro + reprompt_text

    attrs = handler_input.attributes_manager.session_attributes
    attrs["questions"] = game_questions
    attrs["current_question_index"] = 0
    attrs["correct_answer_index"] = correct_slot + 1  # 1-based for comparison
    attrs["correct_answer_text"] = correct_answer_text
    attrs["score"] = 0
    attrs["speech_output"] = reprompt_text
    attrs["reprompt_text"] = reprompt_text

    return (
        handler_input.response_builder
        .speak(speech_output)
        .ask(reprompt_text)
        .set_card(SimpleCard(CARD_TITLE, speech_output))
        .response
    )


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return _start_game(handler_input)


class StartOverIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.StartOverIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return _start_game(handler_input)


class AnswerIntentHandler(AbstractRequestHandler):
    """Handles AnswerIntent (slot: Answer) — the main game loop."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AnswerIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        attrs = handler_input.attributes_manager.session_attributes

        if not attrs.get("questions"):
            speech = "There is no game in progress. Do you want to start a new game? "
            attrs["user_prompted_to_continue"] = True
            return (
                handler_input.response_builder
                .speak(speech)
                .ask(speech)
                .response
            )

        # Validate the answer slot
        slots = handler_input.request_envelope.request.intent.slots
        answer_slot = slots.get("Answer")
        user_answer = None
        if answer_slot and answer_slot.value:
            try:
                user_answer = int(answer_slot.value)
            except ValueError:
                pass

        if user_answer is None or not (1 <= user_answer <= ANSWER_COUNT):
            reprompt = attrs.get("speech_output", "")
            speech = f"Your answer must be a number between 1 and {ANSWER_COUNT}. {reprompt}"
            return (
                handler_input.response_builder
                .speak(speech)
                .ask(reprompt)
                .response
            )

        return _process_answer(handler_input, user_answer, gave_up=False)


class DontKnowIntentHandler(AbstractRequestHandler):
    """Treats DontKnowIntent as a wrong answer and moves on."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("DontKnowIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        attrs = handler_input.attributes_manager.session_attributes
        if not attrs.get("questions"):
            return _start_game(handler_input)
        return _process_answer(handler_input, user_answer=None, gave_up=True)


def _process_answer(handler_input: HandlerInput, user_answer, gave_up: bool) -> Response:
    """Core answer-processing logic shared by AnswerIntent and DontKnowIntent."""
    attrs = handler_input.attributes_manager.session_attributes
    game_questions: list = attrs["questions"]
    correct_answer_index: int = int(attrs["correct_answer_index"])  # 1-based
    current_score: int = int(attrs["score"])
    current_question_index: int = int(attrs["current_question_index"])
    correct_answer_text: str = attrs["correct_answer_text"]

    if gave_up:
        analysis = f"The correct answer is {correct_answer_index}: {correct_answer_text}. "
        prefix = ""
    elif user_answer == correct_answer_index:
        current_score += 1
        analysis = "correct. "
        prefix = "That answer is "
    else:
        analysis = f"wrong. The correct answer is {correct_answer_index}: {correct_answer_text}. "
        prefix = "That answer is "

    if current_question_index == GAME_LENGTH - 1:
        # Game over
        speech = (
            f"{prefix}{analysis}"
            f"You got {current_score} out of {GAME_LENGTH} questions correct. "
            f"Thank you for playing!"
        )
        attrs["score"] = current_score
        return (
            handler_input.response_builder
            .speak(speech)
            .set_card(SimpleCard(CARD_TITLE, speech))
            .set_should_end_session(True)
            .response
        )

    # Advance to next question
    current_question_index += 1
    correct_slot = random.randint(0, ANSWER_COUNT - 1)
    reprompt_text, correct_answer_text = _build_question_speech(
        current_question_index + 1,
        game_questions[current_question_index],
        correct_slot,
    )

    speech = (
        f"{prefix}{analysis}"
        f"Your score is {current_score}. "
        f"{reprompt_text}"
    )

    attrs["current_question_index"] = current_question_index
    attrs["correct_answer_index"] = correct_slot + 1
    attrs["correct_answer_text"] = correct_answer_text
    attrs["score"] = current_score
    attrs["speech_output"] = reprompt_text
    attrs["reprompt_text"] = reprompt_text

    return (
        handler_input.response_builder
        .speak(speech)
        .ask(reprompt_text)
        .set_card(SimpleCard(CARD_TITLE, speech))
        .response
    )


class RepeatIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.RepeatIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        attrs = handler_input.attributes_manager.session_attributes
        speech = attrs.get("speech_output")
        reprompt = attrs.get("reprompt_text")
        if not speech:
            return _start_game(handler_input)
        return (
            handler_input.response_builder
            .speak(speech)
            .ask(reprompt)
            .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        attrs = handler_input.attributes_manager.session_attributes
        attrs["user_prompted_to_continue"] = True
        speech = (
            f"I will ask you {GAME_LENGTH} multiple choice questions. "
            f"Respond with the number of the answer. "
            f"For example, say one, two, three, or four. "
            f"To start a new game at any time, say, start game. "
            f"To repeat the last question, say, repeat. "
            f"Would you like to keep playing?"
        )
        reprompt = (
            "To give an answer to a question, respond with the number of the answer. "
            "Would you like to keep playing?"
        )
        return (
            handler_input.response_builder
            .speak(speech)
            .ask(reprompt)
            .response
        )


class StopCancelIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return (
            is_intent_name("AMAZON.StopIntent")(handler_input)
            or is_intent_name("AMAZON.CancelIntent")(handler_input)
        )

    def handle(self, handler_input: HandlerInput) -> Response:
        return (
            handler_input.response_builder
            .speak("Good bye!")
            .set_should_end_session(True)
            .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input: HandlerInput, exception: Exception) -> bool:
        return True

    def handle(self, handler_input: HandlerInput, exception: Exception) -> Response:
        speech = "Sorry, I had trouble processing that request. Please try again."
        return (
            handler_input.response_builder
            .speak(speech)
            .ask(speech)
            .response
        )


# ---------------------------------------------------------------------------
# Skill builder registration
# ---------------------------------------------------------------------------

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(StartOverIntentHandler())
sb.add_request_handler(AnswerIntentHandler())
sb.add_request_handler(DontKnowIntentHandler())
sb.add_request_handler(RepeatIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(StopCancelIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
