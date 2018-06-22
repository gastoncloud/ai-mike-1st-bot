from app import app
import requests
from jinja2 import Undefined
import json

def split_sentence(sentence):
    return sentence.split("###")


from app.entities.models import Entity
def get_synonyms():
    """
    Build synonyms dict from DB
    :return:
    """
    synonyms = {}

    for entity in Entity.objects:
        for value in entity.entity_values:
            for synonym in value.synonyms:
                synonyms[synonym] = value.value
    app.logger.info("loaded synonyms %s",synonyms)
    return synonyms

def call_api(url, type,headers={}, parameters = {}, is_json=False):
    """
    Call external API
    :param url:
    :param type:
    :param parameters:
    :param is_json:
    :return:
    """
    app.logger.info("Initiating API Call with following info: url => {} payload => {}".format(url,parameters))
    if "GET" in type:
            response = requests.get(url,headers=headers, params=parameters, timeout=5)
    elif "POST" in type:
        if is_json:
            response = requests.post(url,headers=headers, json=parameters, timeout=5)
        else:
            response = requests.post(url,headers=headers, params=parameters, timeout=5)
    elif "PUT" in type:
        if is_json:
            response = requests.put(url,headers=headers, json=parameters, timeout=5)
        else:
            response = requests.put(url,headers=headers, params=parameters, timeout=5)
    elif "DELETE" in type:
        response = requests.delete(url,headers=headers, params=parameters, timeout=5)
    else:
        raise Exception("unsupported request method.")
    result = json.loads(response.text)
    app.logger.info("API response => %s", result)
    return result

class SilentUndefined(Undefined):
    """
    Class to suppress jinja2 errors and warnings
    """

    def _fail_with_undefined_error(self, *args, **kwargs):
        return 'undefined'

    __add__ = __radd__ = __mul__ = __rmul__ = __div__ = __rdiv__ = \
        __truediv__ = __rtruediv__ = __floordiv__ = __rfloordiv__ = \
        __mod__ = __rmod__ = __pos__ = __neg__ = __call__ = \
        __getitem__ = __lt__ = __le__ = __gt__ = __ge__ = __int__ = \
        __float__ = __complex__ = __pow__ = __rpow__ = \
        _fail_with_undefined_error




from functools import reduce
from itertools import groupby
from operator import add, itemgetter

def merge_records_by(key, combine):
    """Returns a function that merges two records rec_a and rec_b.
       The records are assumed to have the same value for rec_a[key]
       and rec_b[key].  For all other keys, the values are combined
       using the specified binary operator.
    """
    return lambda rec_a, rec_b: {
        k: rec_a[k] if k == key else combine(rec_a[k], rec_b[k])
        for k in rec_a
    }

def merge_list_of_records_by(key, combine):
    """Returns a function that merges a list of records, grouped by
       the specified key, with values combined using the specified
       binary operator."""
    keyprop = itemgetter(key)
    return lambda lst: [
        reduce(merge_records_by(key, combine), records)
        for _, records in groupby(sorted(lst, key=keyprop), keyprop)
    ]