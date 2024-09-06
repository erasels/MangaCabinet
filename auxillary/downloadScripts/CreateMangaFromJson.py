import json
import sys


def validate_json(json_input):
    try:
        data = json.loads(json_input)

        # Check if important fields are there
        if 'id' not in data:
            return {"error": "Missing 'id' field"}
        if 'title' not in data:
            return {"error": "Missing 'title' field"}

        return data
    except json.JSONDecodeError as e:
        return {"error": "Invalid JSON", "message": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Requires a json string input."}))

    input_json = sys.argv[1]
    result = validate_json(input_json)
    print(json.dumps(result))
