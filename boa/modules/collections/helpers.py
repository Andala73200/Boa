HELPERS = {
"collection": r'''
def __boa_collection_replace(collection, index, value):
    if isinstance(collection, dict):
        result = dict(collection); result[index] = value; return result
    result = list(collection); result[index] = value; return type(collection)(result) if isinstance(collection, (tuple, set)) else result

def __boa_collection_remove(collection, value):
    if isinstance(collection, dict):
        return {k: v for k, v in collection.items() if k != value}
    result = list(collection); result.remove(value); return type(collection)(result) if isinstance(collection, (tuple, set)) else result
''',
}

