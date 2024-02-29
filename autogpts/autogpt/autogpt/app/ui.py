import json
import logging
import re
import httpx
from inspect import isgenerator, isgeneratorfunction

import gradio as gr

from autogpt.core.model import SignInRequestBody

logger = logging.getLogger(__name__)

SERVER_URL = "http://127.0.0.1:8000/ap/v1"

def is_generator(obj):
    return isgenerator(obj) or isgeneratorfunction(obj)

def list2strs(l, indent=0):
    return "\n".join(["    " * indent +  f"{i + 1}. {item}" for i, item in enumerate(l)])

def consult(message, history):
    
    yield "hey yo"
    
def submit_pet_profile_callback(user_name, pet_type, pet_breed, pet_name):

    response = httpx.post(SERVER_URL + "/agent/setting/pet",
                          json={"pet_name": pet_name,
                                "pet_type": pet_type,
                                "pet_breed": pet_breed,
                                "desc": ""},
                          headers={"Content-Type":"application/json"},
                          timeout=100)
    log_str = ""
    if response.status_code == 200:
        log_str = "🤖 Bot is ready"
    else:
        log_str = "Pet profile submit failed"
    
    return log_str


def bot_callback(msg, hist):

    response = httpx.post(SERVER_URL + "/agent/step",
        json={"input": f"{msg}"},
        headers={"Content-Type":"application/json"},
        timeout=100
    )
    logger.info(f"Response:{response}")

    memory = ""
    reference = ""
    log = ""
    hist += [[None, msg]]
    if response.status_code == 200:
        response_json = response.json()
        agent_output = json.dumps(response_json['output'])
        hist += [[agent_output, None]]
        memory = '\n'.join([
            f'{_}. ' + ' '.join([f"{k}:{v}" for k, v in m.items()])
            for _, m in enumerate(response_json['memory'])])
        reference = response_json['reference']

        log = f"🗣️Your turn to type"
    else:
        log = f"Request Error: {response.status_code}: {response.json()}"

    return None, hist, memory, reference, log


def chat_reset_callback(btn):

    log_str = ""
    response = httpx.post(SERVER_URL + "/agent/history/reset",
                          json={"input":"reset"},
                          headers={"Content-Type":"application/json"},
                          timeout=100)
    if response.status_code == 200:
        log_str = f"{response.text}"
    else:
        log_str = f"Reset request Error: {response.text}"
    
    return [], log_str
    

def reset_func():

    # db.sign_out()

    # return config.DEFAULT_USER_NAME, \
    #     config.DEFAULT_USER_PASSWORD, \
    #     "Xavier", \
    #     [[None, None]], \
    #     "Sign In", \
    #     "App Reset 🔄"

    return ""
    
def sign_func(state, user_name, password, task):
    
    next_state = state
    profile_str = "profile"
    directives_str = "directives"
    commands_str = ""
    log_str = ""
    if state.lower() == "sign in":
        
        try:
            response = httpx.post(SERVER_URL + "/agent/sign_in",
                json={"user_name": user_name, "password": password},
                headers={"Content-Type":"application/json"},
                timeout=100)
            if response.status_code == 200:
                response_json = response.json()
                profile = response_json['ai_profile']
                directives = response_json['directives']
                commands = response_json['commands']
                profile_str = f"Name: {profile['ai_name']}\n"\
                    f"Role: {profile['ai_role']}"
                directives_str = f"Resources:\n" +  list2strs(directives['resources'], 1) + "\n"\
                    f"Constraints:\n" + list2strs(directives['constraints'], 1) + "\n"\
                    f"Best Practices:\n" + list2strs(directives['best_practices'], 1) + "\n"
                commands_str = list2strs(commands)
                next_state = "Sign Out"
                log_str += "Sign In succeeds ✅ !\n" + submit_task_callback(task)
        except Exception as e:
            logger.warning(f"Sign in Request Error: {e}")
            log_str += "Sign In failed ❌ Please check your User Name / Password"
    elif state.lower() == "sign out":
        try:
            response = httpx.post(SERVER_URL + "/agent/sign_out",
                                  json={"input":"sign out"},
                                  headers={"Content-Type": "application/json"},
                                  timeout=100)
            if response.status_code == 200:
                pass
            log_str += "Sign Out succeeds ✅"
        except Exception as e:
            logger.warning(f"Sign out Request Error: {e}")
            log_str += "Sign Out failed ❌"
        next_state = "Sign In"

    return next_state, log_str, profile_str, directives_str, commands_str

def create_agent_callback(desc):

    response = httpx.post(SERVER_URL + "/agent/create",
        json={"input": f"{desc}"},
        headers={"Content-Type":"application/json"}, 
        timeout=100)
    logger.info(f"Response:{response}")

    profile_str = "profile"
    directives_str = "directives"
    commands_str = ""
    log_str = "👾Agent init failed"
    if response.status_code == 200:
        response_json = response.json()
        profile = eval(response_json['profile'])
        profile_str = f"Name: {profile['ai_name']}\n"\
            f"Role: {profile['ai_role']}"
        directives = eval(response_json['directives'])
        directives_str = f"Resources:\n" +  list2strs(directives['resources'], 1) + "\n"\
            f"Constraints:\n" + list2strs(directives['constraints'], 1) + "\n"\
            f"Best Practices:\n" + list2strs(directives['best_practices'], 1) + "\n"
        commands_str = list2strs(response_json['commands'])
        log_str =  "🤖Agent init succeed"

    return profile_str, directives_str, commands_str, log_str
    

def submit_agent_profile_callback(profile: str) -> str:
    
    def decode_profile(s: str) -> dict:
        s = s.strip().split("\n")
        try:
            assert len(s) == 2, f"Length of profile violation {len(s)}, {s}"
            assert "Name:" in s[0], f"Format error: {s[0]}, has not 'Name' attribute"
            name = ':'.join(s[0].split(':')[1:]).strip()
            assert "Role:" in s[1], f"Format error: {s[1]}, has not 'Role' attribute"
            role = ':'.join(s[1].split(':')[1:]).strip()
            return {"name": name, "role": role}
        except Exception as e:
            logger.warning(f"Decode profile error {e}")
        
        return {}
    
    response = httpx.post(SERVER_URL + "/agent/setting/profile",
                          json={"input": f"{decode_profile(profile)}"},
                          headers={"Content-Type": "application/json"},
                          timeout=100)
    response_dict = eval(response.json())
    new_profile = f"Name: {response_dict['ai_name']}\n"\
        f"Role: {response_dict['ai_role']}"
    if response.status_code == 200:
        return new_profile, f"✅ Update profile succeeded"
    else:
        return new_profile, f"❌ Update profile failed"

def submit_directives_callback(directives: str) -> str:
    
    def decode_directives(s: str) -> dict:
        # Example input
        #   Resources:
        #   1. Internet access for searches and information gathering.
        #   Constraints:
        #   1. Exclusively use the commands listed below.
        #   Best Practices:
        #   1. Continuously review and analyze your actions to ensure you are performing to the best of your abilities.
        lines = s.split("\n")
        keywords = {"Resources": 0, "Constraints": 0, "Best Practices": 0}
        decoded = {k: [] for k in keywords}
        i = 0
        j = 0
        cur_keyword = ""
        pattern = re.compile("\d+\.(.+)")
        while i < len(lines):
            if not cur_keyword:
                for k in keywords:
                    if keywords[k] == 0 and k in lines[i]:
                        cur_keyword = k
                        keywords[k] = 1
                        break
                if not cur_keyword:
                    break
            else:
                line = lines[i].strip()
                match = pattern.match(line)
                if match:
                    extracted_str = match.group(1).strip()
                    decoded[cur_keyword].append(extracted_str)
                else:
                    cur_keyword = ""
                    continue
            i += 1
                
        return decoded

    response = httpx.post(SERVER_URL + "/agent/setting/directives",
                          json={"input":f"{decode_directives(directives)}"},
                          headers={"Content-Type": "application/json"},
                          timeout=100)
    try:
        response_dict = eval(response.json())
        new_directives = f"Resources:\n" +  list2strs(response_dict['resources'], 1) + "\n"\
            f"Constraints:\n" + list2strs(response_dict['constraints'], 1) + "\n"\
            f"Best Practices:\n" + list2strs(response_dict['best_practices'], 1) + "\n"
        if response.status_code == 200:
            return new_directives, f"✅ Update directives succeeded"
        else:
            return new_directives, f"❌ Update directives failed"
    except Exception as e:
        logger.warning(f"Retrieve agent directives Error: {e}")
    
    return directives, f"❌ Update directives failed"

def submit_task_callback(task: str) -> str:
    
    response = httpx.post(SERVER_URL + "/agent/setting/task",
                          json={"input": f"{task}"},
                          headers={"Content-Type": "application/json"},
                          timeout=100)
    try:
        response_str = response.text
        if response.status_code == 200:
            return f"✅ Setting task succeed"
        else:
            return f"❌ Request to setting task error"
    except Exception as e:
        return f"❌ Process task setting error"
    
PET_TYPES = ["Cat", "Dog"]
TASK_TYPES = ["Diagnosis", "Caring"]

with gr.Blocks() as demo:
    
    with gr.Column():
        gr.Markdown(
            """
            # Pet Consultation Demo
            ## User Guide
            Sign In ➡️ Submit Pet Profile ➡️ Chat ! ➡️ (Reset)
            """)
        with gr.Row():
            with gr.Column():
                with gr.Row():
                    with gr.Column():
                        gr.Markdown(
                            """
                            ## Sign in </center>
                            """)
                        # user_name_text = gr.Textbox(label="User Name", value=config.DEFAULT_USER_NAME)
                        # password_text = gr.Textbox(label="Password", value=config.DEFAULT_USER_PASSWORD, type='password')
                        user_name_text = gr.Textbox(label="User Name", value="root@chat.com")
                        password_text = gr.Textbox(label="Password", value="123456", type='password')
                        sign_btn = gr.Button(value="Sign In")
                    with gr.Column():
                        gr.Markdown(
                            """
                            ## Pet profile
                            """)
                        pet_type_dd = gr.Dropdown(PET_TYPES, label="Pet Type", value=PET_TYPES[0])
                        pet_breed_text = gr.Textbox(label="Pet Breed", value="Maine Coon")
                        pet_name_text = gr.Textbox(label="Pet Name", value="Xavier")
                        pet_profile_btn = gr.Button(value="Submit")

                with gr.Column():
                    gr.Markdown(
                        """
                        ## Chat
                        """)
                    chat_memory_text = gr.Textbox(label="Memory")
                    chat_reference_text = gr.Textbox(label="Reference")
                    chatbot = gr.Chatbot(scale=4)
                    user_input = gr.Textbox(label="User Input", scale=1)
                    chat_reset_btn = gr.Button(value="Reset Chat")

            with gr.Column():
                gr.Markdown(
                    """
                    ## Agent Settings
                    """
                )
                profile_text = gr.Textbox(label="Profile", info="editable")
                directives_text = gr.Textbox(label="Directives", info="editable")
                commands_text = gr.Textbox(label="Commands")
                task_text = gr.Textbox(label="Task Desc", info="editable", value="Try to help diagnosis any diseases step by step when the user sort for help")
                task_dd = gr.Dropdown(TASK_TYPES, label="Task Name", value=TASK_TYPES[0])
                desc_text = gr.Textbox(label="Description", info="editable", value="You are a vet AI assitant, help with consultants")
                create_agent_btn = gr.Button(value="Create")
                
        reset_btn = gr.Button(value="Reset")
        log_text = gr.Textbox(label="Running Log")

        # bindings
        sign_btn.click(sign_func, [sign_btn, user_name_text, password_text, task_text], [sign_btn, log_text, profile_text, directives_text, commands_text])
        user_input.submit(bot_callback, [user_input, chatbot], [user_input, chatbot, chat_memory_text, chat_reference_text, log_text])
        pet_profile_btn.click(submit_pet_profile_callback, 
                              inputs=[user_name_text, pet_type_dd, pet_breed_text, pet_name_text], 
                              outputs=[log_text])
        profile_text.submit(submit_agent_profile_callback, profile_text, [profile_text, log_text]) 
        directives_text.submit(submit_directives_callback, directives_text, [directives_text, log_text])
        task_text.submit(submit_task_callback, task_text, log_text)
        reset_btn.click(reset_func, None, 
            [user_name_text, password_text, pet_name_text, chatbot, sign_btn, log_text])

        create_agent_btn.click(create_agent_callback, desc_text, [profile_text, directives_text, commands_text, log_text])

        chat_reset_btn.click(chat_reset_callback, [chat_reset_btn], [chatbot, log_text])