class ContextManager():
    def __init__(self,global_context,intent_contexts,intent):
        self.context_memory = global_context
        self.input_contexts = intent_contexts.get("inputContexts")
        self.output_contexts = intent_contexts.get("outputContexts")
        self.intent = intent

    def upsert_context(self,context,params):
        pass

    def set_contexts(self,contexts,parameters={}):
        """
        {
            "name": "account_balance_check_dialog_params_account",
            "parameters": {
              "account.original": "",
              "account": ""
            },
            "lifespan": 1
        }

        :param contexts:
        :param params:
        :return:
        """
        self.unset_contexts()
        for context in self.output_contexts:

            for existing_context in self.context_memory:
                if context == existing_context.get("name"):
                    existing_context.get("parameters").extent(parameters)
                existing_context.update((k, "value3") for k, v in d.items() if v == "value2")


    def unset_contexts(self):
        self.context_memory = {}

    def find_intent(self,intent,entities={}):

        intents = [ self.flow_data[intent]  for intent in self.flow_data.keys() if query in intent ]

        for intent in intents:
            if  set(intent.get("input_context")).issubset(set(self.current_contexts)):
                return intent
        return self.default_intents["fallback"]