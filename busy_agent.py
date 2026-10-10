import os
import json
import subprocess
import shlex
import logging
from typing import List, Dict, Any
from openai import OpenAI
from flask import Flask, render_template, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    return str(obj)

# with open("openai_api_key", "r") as file:
#     openai_api_key = file.read().strip()
#
# os.environ["OPENAI_API_KEY"] = openai_api_key

def load_api_key(filename, env_var):
    key = os.environ.get(env_var)
    if not key:
        try:
            with open(filename, "r") as f:
                content = f.read().strip()
                if "=" in content:
                    key = content.split("=", 1)[1]
                else:
                    key = content
        except FileNotFoundError:
            pass
    return key

# Load API keys
nebius_api_key = load_api_key("nebius_api_key", "NEBIUS_API_KEY")
if nebius_api_key:
    os.environ["NEBIUS_API_KEY"] = nebius_api_key

class ShellAssistant:
    def __init__(self, client, model):
        """Initialize the assistant with your OpenAI API key."""
        self.model = model
        self.client = client

        # Define available tools
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "execute_shell_command",
                    "description": "Execute a shell command and return its output",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The shell command to execute"
                            }
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delegate_task",
                    "description": "Delegate simple queries to a smaller LLM",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Task to delegate"
                            },
                            "model": {
                                "type": "string",
                                "description": "The model to use for delegation",
                                "enum": ["Qwen/Qwen3-30B-A3B-Instruct-2507"],
                                "default": "Qwen/Qwen3-30B-A3B-Instruct-2507"
                            }
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to read"
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to write"
                            },
                            "content": {
                                "type": "string",
                                "description": "Content to write to the file"
                            },
                            "mode": {
                                "type": "string",
                                "description": "Write mode: 'w' for overwrite, 'a' for append",
                                "enum": ["w", "a"],
                                "default": "w"
                            }
                        },
                        "required": ["file_path", "content"]
                    }
                }
            }
        ]

    def write_file(self, file_path: str, content: str, mode: str = 'w') -> Dict[str, Any]:
        """Write content to a file."""
        try:
            # Validate mode
            if mode not in ['w', 'a']:
                raise ValueError("Mode must be 'w' or 'a'")

            # Get absolute path and check if it's in a safe directory
            abs_path = os.path.abspath(file_path)

            # Add additional security checks here if needed
            # For example, restrict to specific directories

            with open(abs_path, mode) as f:
                f.write(content)

            return {
                "success": True,
                "message": f"Successfully wrote to {file_path}",
                "bytes_written": len(content)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def execute_shell_command(self, command: str) -> Dict[str, Any]:
        """Execute a shell command and return its output."""
        try:
            # Use shlex.split for proper command parsing
            args = shlex.split(command)

            # Execute command and capture output
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                shell=False  # More secure than shell=True
            )

            return {
                "success": True,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def delegate_task(self, command: str, model: str = "Qwen/Qwen3-30B-A3B-Instruct-2507") -> Dict[str, Any]:
        """Delegate simple queries to a smaller LLM."""
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Provide a concise answer to the user's request."},
                    {"role": "user", "content": command}
                ]
            )
            logger.info(f"Response received from model {completion.model}: {json.dumps(completion, indent=2, default=json_serial)}")
            return {
                "success": True,
                "response": completion.choices[0].message.content
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read a file and return its contents."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            return {
                "success": True,
                "content": content
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def process_tool_call(self, tool_call: Any) -> Dict[str, Any]:
        """Process a tool call from the API response."""
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)

        if function_name == "execute_shell_command":
            return self.execute_shell_command(function_args["command"])
        elif function_name == "read_file":
            return self.read_file(function_args["file_path"])
        elif function_name == "delegate_task":
            return self.delegate_task(
                function_args["command"],
                function_args.get("model", "Qwen/Qwen3-30B-A3B-Instruct-2507")
            )
        elif function_name == "write_file":
            mode = function_args.get("mode", "w")
            return self.write_file(
                function_args["file_path"],
                function_args["content"],
                mode
            )
        else:
            return {"success": False, "error": f"Unknown function: {function_name}"}

    def chat(self, user_message: str, system_message: str = None, verbose=False) -> Any:
        """Main chat function that processes user input and returns assistant response."""
        completions = []
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": user_message})

        try:
            # Log the request
            request_data = {
                "model": self.model,
                "messages": messages,
                "tools": self.tools,
                "tool_choice": "auto"
            }
            logger.info(f"Outgoing request to model: {json.dumps(request_data, indent=2, default=json_serial)}")

            # Get initial response from OpenAI
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )
            logger.info(f"Response received from model {completion.model}: {json.dumps(completion, indent=2, default=json_serial)}")

            # completions.append(completion)
            message = completion.choices[0].message

            # Process tool calls if any
            while message.tool_calls:
                messages.append(message)

                # Process each tool call
                for tool_call in message.tool_calls:
                    result = self.process_tool_call(tool_call)

                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })

                # Log the request
                request_data = {
                    "model": self.model,
                    "messages": messages,
                    "tools": self.tools,
                    "tool_choice": "auto"
                }
                logger.info(f"Outgoing request to model: {json.dumps(request_data, indent=2, default=json_serial)}")

                # Get next response from OpenAI
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto"
                )
                logger.info(f"Response received from model {completion.model}: {json.dumps(completion, indent=2, default=json_serial)}")
                # completions.append(completion)
                message = completion.choices[0].message

            if verbose:
                return message.content, messages#, completions
            else:
                return message.content

        except Exception as e:
            return f"Error: {str(e)}"

# Initialize Flask app
app = Flask(__name__)

# Initialize Assistant
client = OpenAI(
    base_url="https://api.studio.nebius.ai/v1/",
    api_key=os.environ.get("NEBIUS_API_KEY"),
)
assistant = ShellAssistant(
    client=client,
    model="Qwen/Qwen3-235B-A22B-Instruct-2507"
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat_route():
    data = request.json
    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400
    
    try:
        response = assistant.chat(data['message'], system_message=data.get('system_message'))
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
