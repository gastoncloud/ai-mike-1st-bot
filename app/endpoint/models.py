class ContextManager():
    def __init__(self,context_memory,request_context= {}):
        self.context_memory  = context_memory or []
        self.request_context = request_context
        self.intent = None

    def update_request_context(self,new_context):
        self.request_context.update(new_context)

    def get_request_context(self):
        context_memory_flat =  {
         context.get("name"):context.get("parameters",{}) for context in self.context_memory
        }
        self.request_context.update(context_memory_flat)

        return self.request_context

    def update_context_memory(self,intent,parameters={}):
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
        # self.unset_contexts()
        # create output contexts

        output_contexts = []

        for context in self.intent.outputContexts:
            output_contexts.append({
                "name":context,
                "parameters":parameters
            })

        from .utils import merge_list_by_key

        self.context_memory = self.context_memory + output_contexts
        # self.context_memory= merge_list_by_key(self.context_memory,output_contexts,"name")

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