import json
from jinja2 import Template
from flask import Blueprint, request, abort
from app import app
from app.commons.logger import logger
from app.commons import build_response
from app.nlu.entity_extractor import EntityExtractor
from app.nlu.tasks import model_updated_signal
from app.intents.models import Intent
from app.endpoint.utils import get_synonyms, SilentUndefined, split_sentence, call_api
from app.agents.models import Bot

endpoint = Blueprint('api', __name__, url_prefix='/api')

from app.nlu.classifiers.starspace_intent_classifier import EmbeddingIntentClassifier

sentence_classifier = None
synonyms = None
entity_extraction = None


# Request Handler
@endpoint.route('/v1', methods=['POST'])
def api():
    """
    Endpoint to converse with chatbot.
    Chat context is maintained by exchanging the payload between client and bot.

    sample input/output payload =>

    {
      "currentNode": "",
      "complete": false,
      "parameters": [],
      "extractedParameters": {},
      "missingParameters": [],
      "intent": {
      },
      "context": [],
      "input": "hello",
      "event":"welcome",
      "speechResponse": [
      ]
    }

    :param json:
    :return json:
    """
    request_json = request.get_json(silent=True)
    is_event = False

    if request_json:
        result_json = request_json
        intent = None
        request_context = {}
        new_intent_flag = (request_json.get("complete") is None) or request_json.get("complete")

        from .models import ContextManager
        context_manager = ContextManager(request_json["context"])

        # check if input method is event or raw text
        if request_json.get("event"):
            query_intent_id = request_json.get("event")
            confidence = 1
            is_event = True

        elif request_json.get("input"):
            query_intent_id, confidence, suggetions = predict(request_json.get("input"))
        else:
            abort(400, "invalid request")

        if new_intent_flag:
            intent_id = query_intent_id
        else:
            intent_id = request_json["intent"]["id"]

        intent = Intent.objects.get(intentId=intent_id.strip())

        # add intent information to final payload
        result_json["intent"] = {
            "object_id": str(intent.id),
            "confidence": confidence,
            "id": str(intent.intentId),
            "fullFillExternally": request_json["intent"].get("fullFillExternally")  \
                if "fullFillExternally" in request_json["intent"] else intent.fullFillExternally
        }
        app.logger.info("*******************************" + query_intent_id)
        app.logger.info("*******************************" + str("cancel" != query_intent_id))
        if ("cancel" == query_intent_id):
            result_json["currentNode"] = None
            result_json["missingParameters"] = []
            result_json["parameters"] = {}
            result_json["intent"] = {
                "confidence": 1,
                "id": "cancel",
                "fullFillExternally":False
            }
            result_json["context"] = result_json["context"][0]
            result_json["complete"] = True
            intent = Intent.objects.get(intentId="cancel")
        elif new_intent_flag:
            if intent.parameters:
                # Extract NER entities
                if  is_event:
                    extracted_parameters =  request_json.get("extractedParameters") or {}
                else:
                    extracted_parameters = {}
                    extracted_parameters.update(entity_extraction.predict(intent_id,
                                                                 request_json.get("input")))

                # initialize context manage
                missing_parameters = []
                result_json["missingParameters"] = []
                result_json["parameters"] = []

                for parameter in intent.parameters:
                    result_json["parameters"].append({
                        "name": parameter.name,
                        "type": parameter.type,
                        "required": parameter.required
                    })

                    if parameter.required:
                        if parameter.name not in extracted_parameters.keys():
                            result_json["missingParameters"].append(
                                parameter.name)
                            missing_parameters.append(parameter)

                result_json["extractedParameters"] = extracted_parameters

                if missing_parameters:
                    result_json["complete"] = False
                    current_node = missing_parameters[0]
                    result_json["currentNode"] = current_node["name"]
                    result_json["speechResponse"] = split_sentence(current_node["prompt"])
                else:
                    result_json["complete"] = True
            else:
                result_json["complete"] = True

        elif request_json.get("complete")==False and request_json.get("currentNode"):

            extracted_parameter = entity_extraction.replace_synonyms({
                request_json.get("currentNode"): request_json.get("input")
            })

            # replace synonyms for entity values
            result_json["extractedParameters"].update(extracted_parameter)

            result_json["missingParameters"].remove(request_json.get("currentNode"))

            if len(result_json["missingParameters"]) == 0:
                result_json["complete"] = True
                context_manager.update_request_context(result_json["extractedParameters"])
            else:
                missing_parameter = result_json["missingParameters"][0]
                result_json["complete"] = False
                current_node = [node for node in intent.parameters if missing_parameter == node.name][0]
                result_json["currentNode"] = current_node.name
                result_json["speechResponse"] = split_sentence(current_node.prompt)
        else:
            pass

        if result_json["complete"]:
            context_manager.update_request_context(result_json["extractedParameters"])
            context_manager.update_context_memory(intent, result_json["extractedParameters"])
            app.logger.info("$$$$$$$$$$$$ COMPLETED")
            app.logger.info(context_manager.request_context)
            if intent.apiTrigger:
                if result_json["intent"].get("fullFillExternally") == False:
                    isJson = False
                    parameters = result_json["extractedParameters"]
                    headers = intent.apiDetails.get_headers()
                    app.logger.info("headers %s" % headers)
                    url_template = Template(
                        intent.apiDetails.url, undefined=SilentUndefined)
                    rendered_url = url_template.render(**context_manager.get_request_context())
                    if intent.apiDetails.isJson:
                        isJson = True
                        request_template = Template(
                            intent.apiDetails.jsonData, undefined=SilentUndefined)
                        parameters = json.loads(request_template.render(**context_manager.get_request_context()))

                    try:
                        result = call_api(rendered_url,
                                          intent.apiDetails.requestType, headers,
                                          parameters, isJson)
                    except Exception as e:
                        app.logger.warn("API call failed", e)
                        result_json["speechResponse"] = ["Service is not available. Please try again later."]
                    else:
                        context_manager.update_request_context({
                            "result": result
                        })
                        template = Template(
                            intent.speechResponse, undefined=SilentUndefined)
                        result_json["speechResponse"] = split_sentence(
                        template.render(**context_manager.get_request_context()))
                        if intent.endOfConversation:
                            result_json["endOfConversation"] = True
                else:
                    result_json["complete"] = False
                    result_json["speechResponse"] = ["Please wait.."]
            else:
                template = Template(intent.speechResponse,
                                    undefined=SilentUndefined)
                app.logger.info(context_manager.get_request_context())
                result_json["speechResponse"] = split_sentence(template.render(**context_manager.get_request_context()))
                if intent.endOfConversation:
                    result_json["endOfConversation"] = True

            if is_event and result_json["intent"].get("fullFillExternally") == False:
                del result_json["event"]

        if result_json["intent"]["fullFillExternally"] == False:
            result_json["intent"].pop("fullFillExternally")
            result_json["context"] = context_manager.context_memory
            logger.info(request_json.get("input"), extra=result_json)
        return build_response.build_json(result_json)
    else:
        return abort(400)


def update_model(app, message, **extra):
    """
    Signal hook to be called after training is completed.
    Reloads ml models and synonyms.
    :param app:
    :param message:
    :param extra:
    :return:
    """
    global sentence_classifier

    sentence_classifier = EmbeddingIntentClassifier.load(app.config["MODELS_DIR"])
    synonyms = get_synonyms()
    global entity_extraction
    entity_extraction = EntityExtractor(synonyms)
    app.logger.info("Intent Model updated")


# Loading ML Models at app startup
with app.app_context():
    update_model(app, "Modles updated")

model_updated_signal.connect(update_model, app)


def predict(sentence):
    """
    Predict Intent using Intent classifier
    :param sentence:
    :return:
    """
    bot = Bot.objects.get(name="default")
    predicted, intents = sentence_classifier.process(sentence)
    app.logger.info("predicted intent %s", predicted)
    if predicted["confidence"] < bot.config.get("confidence_threshold", .90):
        return Intent.objects(intentId=app.config["DEFAULT_FALLBACK_INTENT_NAME"]).first().intentId, 1.0, []
    else:
        return predicted["intent"], predicted["confidence"], intents[1:]
