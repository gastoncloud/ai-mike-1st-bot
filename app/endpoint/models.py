class ContextManager():
    def __init__(self,context_memory):
        self.context_memory = context_memory or []
        self.intent = None

    def upsert_context(self,context,params):
        pass

    def get_contexts(self):
        return {
         context.get("name"):context.get("parameters",{}) for context in self.context_memory
        }

    def update_contexts(self,intent,parameters={}):
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
        self.intent = intent
        self.unset_contexts()
        # create output contexts

        output_contexts = []

        for context in self.intent.outputContexts:
            output_contexts.append({
                "name":context,
                "parameters":parameters
            })

        from .utils import merge_list_of_records_by,add

        merger = merge_list_of_records_by('name', add)
        self.context_memory= merger(self.context_memory + output_contexts)

        # for context in self.output_contexts:
        #     for existing_context in self.context_memory:
        #         if context == existing_context.get("name"):
        #             existing_context.get("parameters").extent(parameters)

    def unset_contexts(self):
        self.context_memory = []

    def find_intent(self,intent,entities={}):

        # intents = [ self.flow_data[intent]  for intent in self.flow_data.keys() if query in intent ]
        #
        # for intent in intents:
        #     if  set(intent.get("input_context")).issubset(set(self.current_contexts)):
        #         return intent
        # return self.default_intents["fallback"]
        pass