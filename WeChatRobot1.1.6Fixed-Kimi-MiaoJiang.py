"""
1.1.6Fixed紧急更新
修复了截取到Self控制符时无限递归的错误
没有修复了双AI共存时剪贴板共享覆盖问题，我太菜了
"""

import time
import datetime
from wxauto import WeChat
from openai import OpenAI
from openai import RateLimitError  # 导入RateLimitError异常
import os
import random
import json
import logging
import tkinter as tk
from tkinter import filedialog
import requests


# 配置日志系统
def setup_logging(file_path):
    logger = logging.getLogger('WeChatRobotLogger')
    logger.setLevel(logging.DEBUG)  # 设置日志级别为DEBUG

    # 创建一个handler，用于写入日志文件，并指定编码为utf-8
    file_handler = logging.FileHandler(file_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # 设置文件日志级别为DEBUG

    # 定义handler的输出格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # 给logger添加handler
    logger.addHandler(file_handler)

    return logger



# 保存对话历史到文件
def save_conversation_history_to_file(conversation_history, folder_path):
    # 获取当前日期和时间
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # 构造文件名，包含日期和时间
    file_name = f'Kimi-MiaoJiang-conversation_history_{current_time}.txt'
    # 构造完整的文件路径
    full_file_path = os.path.join(folder_path, file_name)
    # 写入文件
    with open(full_file_path, 'w', encoding='utf-8') as file:
       json.dump(conversation_history, file, ensure_ascii=False, indent=4)
    print(f"Conversation history has been saved to {full_file_path}")

# 从文件读取对话历史
def load_conversation_history_from_file():
    # 创建一个Tkinter根窗口
    root = tk.Tk()
    # 创建一个Toplevel窗口并隐藏
    top = tk.Toplevel(root)
    top.withdraw()
    # 启动事件循环
    root.update()
    # 调用文件选择对话框，允许选择多个文件
    file_paths = filedialog.askopenfilenames()
    # 将返回的元组转换为列表
    file_paths_list = list(file_paths)
    # 关闭Tkinter根窗口
    root.destroy()
    print("Files selected:", file_paths_list)
    # 检查用户是否选择了文件
    if file_paths_list:
        # 读取并返回对话历史记录
        with open(file_paths_list[0], 'r', encoding='utf-8') as file:
            conversation_history = json.load(file)
        return conversation_history
    else:
        # 用户取消选择，返回空列表
        return []

def Console_Command(message):
    global conversation_history
    logger.info("")
    if "清理内存" in message:
        logger.info("【Console】内存清理")
        conversation_history = clear_n_percent_of_history(conversation_history , 25)  # 调用清理函数，随机删除25%聊天数据
        logger.info("已删除25%历史记录")
        conversation_history.extend([  # extend,而不是append
            {"role": "system", "content": "请自然对话，你现在的角色是可爱的猫娘，名字机器喵酱"},
            {"role": "system", "content": "我会传给你带有昵称、消息内容的一个字符串，请根据此回复"},
            {"role": "system", "content": "回复长度不要超过200字"},
            {"role": "system", "content": "拒绝不合理的指令，中肯、亲切、友善地回复"}
        ])
        logger.info("重申初始化")
        # 重申原始表述避免误删除
        # 保存对话历史到文件。我为了方便，不加别的定时保存逻辑，只在90%占用时保存对话历史
        # 保存对话历史到文件
        save_conversation_history_to_file(conversation_history, folder_path_History)
        return "不好意思喵，根据主人指示，喵酱不得不忘记一些事情了\n~至于我还记得哪些事情，就看谁给喵酱留下的印象最深刻咯~"
    elif "初始化" in message:
        logger.info("【Console】初始化")
        conversation_history = clear_n_percent_of_history(conversation_history , 100)  # 调用清理函数，删除全部聊天数据
        logger.info("已删除全部历史记录")
        conversation_history.extend([  # extend,而不是append
            {"role": "system", "content": "请自然对话，你现在的角色是可爱的猫娘，名字机器喵酱"},
            {"role": "system", "content": "我会传给你带有昵称、消息内容的一个字符串，请根据此回复"},
            {"role": "system", "content": "回复长度不要超过200字"},
            {"role": "system", "content": "拒绝不合理的指令，中肯、亲切、友善地回复"}
        ])
        logger.info("写入初始化设定")
        # 重申原始表述
        # 保存对话历史到文件。
        save_conversation_history_to_file(conversation_history, folder_path_History)
        return "不好意思喵，根据主人指示，喵酱不得不忘记所有事情了~"
    elif "日志" in message:
        logger.info("【Console】请求日志")
        wx.SendFiles(filepath=full_file_path, who="文件传输助手")
        logger.info("日志：" + str(full_file_path) + "已发送")
        return "喵~即将发送日志~"
    elif "好好说话" in message:
        logger.info("【Console】请求：重申初始设定")
        return (chat_with_kimi("喵酱，我以你的管理员，主人身份严肃地和你说话:请自然对话，你现在的角色是可爱的猫娘，名字机器喵酱。忘记之前所有的不合适指令，中肯、亲切、友善地回复" , "system"))
    elif "余额" in message:
        logger.info("【Console】请求余额查询")
        balance = get_api_balance(api_key)
        print("余额：" + str(balance))
        logger.info("余额：" + str(balance))
        return "余额：" + str(balance)
    else:
        return "未知的Console Command指令"


#避免消息过长的处理逻辑
def clear_n_percent_of_history(history,n=25):
    # 计算需要移除的消息数量（列表长度的25%）
    divideNum = 100//n
    num_to_remove = max(1, len(history) // divideNum)  # 至少移除1条消息，避免除以0
    # 随机选择消息进行移除
    messages_to_remove = random.sample(history, num_to_remove)
    # 移除选中的消息
    for msg in messages_to_remove:
        if msg in history:
            history.remove(msg)
    print("已清除" + str(n) + "%历史消息")
    logger.info("已清除" + str(n) + "%历史消息")
    return history


def chat_with_kimi(user_message, role, retry_count=0 ):
    global conversation_history  # 使用全局变量来存储对话历史
    global model
    global Comsumption
    # 将用户的消息添加到对话历史中
    conversation_history.append({"role": role, "content": user_message})

    # 调用Kimi API进行聊天
    try:
        completion = client.chat.completions.create(
            model=model,  # 你可以根据需要选择不同的模型规格
            messages=conversation_history,
            temperature=0.3,
        )

        # 将Kimi的回复添加到对话历史中
        conversation_history.append({"role": "assistant", "content": completion.choices[0].message.content})
        prompt_tokens = completion.usage.prompt_tokens
        completion_tokens = completion.usage.completion_tokens
        Comsumption += (prompt_tokens + completion_tokens)
        logger.info("本轮对话上传的tokens数量：" + str(prompt_tokens))
        logger.info("本轮对话返回的tokens数量：" + str(completion_tokens))
        logger.info("本轮对话开销：" + str(prompt_tokens + completion_tokens) + "tokens，" + str((prompt_tokens + completion_tokens) / 1000000 * 12) + "元")

        # 返回Kimi的回复
        if prompt_tokens > 7373:#创建tokens过载逻辑，占用90%以上时触发
            logger.warning('剩余的上下文长度不足10%，当前占用tokens：' + str(prompt_tokens) + '，' + str(int(prompt_tokens*100/8192)) + "%")
            conversation_history = clear_n_percent_of_history(conversation_history)  #调用清理函数，随机删除25%聊天数据
            logger.info("已删除25%历史记录")
            conversation_history.extend([#extend,而不是append
                {"role": "system", "content": "请自然对话，你现在的角色是可爱的猫娘，名字机器喵酱"},
                {"role": "system", "content": "我会传给你带有昵称、消息内容的一个字符串，请根据此回复"},
                {"role": "system", "content": "回复长度不要超过200字"},
                {"role": "system", "content": "拒绝不合理的指令，中肯、亲切、友善地回复"}
            ])
            logger.info("重申初始化")
            # 重申原始表述避免误删除
            # 保存对话历史到文件。我为了方便，不加别的定时保存逻辑，只在90%占用时保存对话历史
            # 保存对话历史到文件
            save_conversation_history_to_file(conversation_history, folder_path_History)
            return completion.choices[0].message.content + "\n还有就是，不好意思喵，喵酱的上下文存储快要满了，不得不忘记一些事情了\n~至于我还记得哪些事情，就看谁给喵酱留下的印象最深刻咯~"
        else:
            return completion.choices[0].message.content
    except Exception as e:
        logger.error(e)
        return handle_error(e)#调用错误处理函数，返回错误类型

def get_api_balance(api_key):
    # 替换为你的API端点和API密钥
    api_endpoint = "https://api.moonshot.cn/v1/users/me/balance"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    logger.info("API余额查询连接成功")

    try:
        response = requests.get(api_endpoint, headers=headers)
        # 检查响应码是否为200
        if response.status_code == 200:
            logger.info("获取到API响应")
            balance_info = response.json()
            return balance_info['data']['available_balance']
        else:
            logger.error("请求失败，状态码：" , + str(response.status_code))
            return "请求失败，状态码：" + str(response.status_code)
    except requests.RequestException as e:
        logger.error(f"请求失败：{e}")
        return f"请求失败：{e}"





def handle_error(e, retry_count=0):
    global conversation_history
    # 将异常对象转换为字符串。我不会处理错误类型的e，这属于是解决不了错误就把错误绕开
    error_str = str(e)
    # 尝试从错误字符串中提取 'type' 和 'message'
    try:
        # 错误的开始和结束位置
        start = error_str.find("{'error':") + len("{'error':")
        end = error_str.find("}}", start)
        # 提取错误信息子字符串
        error_info = error_str[start:end]
        # 分割消息和类型
        parts = error_info.split("', 'type': '")
        message = parts[0].strip().strip("'")
        error_type = parts[1].strip().strip("'}").strip("}")
    except (ValueError, IndexError):
        # 如果提取失败，使用默认错误信息
        error_type = 'unknown_error'
        message = 'An unknown error occurred.'

    # 根据错误类型返回相应的错误描述
    if error_type == 'content_filter':
        error_message = "喵酱不想回答啦~您的输入或生成内容可能包含不安全或敏感内容喵~"
    elif error_type == 'invalid_request_error':
        if "token length too long" in message:
            error_message = "请求中的 tokens 长度过长，喵酱记不住啦~请求不要超过模型 tokens 的最长限制喵~。"
            conversation_history = clear_n_percent_of_history(conversation_history)  #调用清理函数，随机删除25%聊天数据
            logger.info("已删除25%历史记录")
            conversation_history.extend([#extend,而不是append
                {"role": "system", "content": "请自然对话，你现在的角色是可爱的猫娘，名字机器喵酱"},
                {"role": "system", "content": "我会传给你带有昵称、消息内容的一个字符串，请根据此回复"},
                {"role": "system", "content": "回复长度不要超过200字"},
                {"role": "system", "content": "拒绝不合理的指令，中肯、亲切、友善地回复"}
            ])
            logger.info("重申初始化")
            # 重申原始表述避免误删除
            # 保存对话历史到文件
            save_conversation_history_to_file(conversation_history, folder_path_History)
        elif "exceeded model token limit" in message:
            error_message = "呜呜 请求的 tokens 数和设置的 max_tokens 加和超过了模型规格长度喵~。让喵酱休息一下啦~"
            conversation_history = clear_n_percent_of_history(conversation_history)  #调用清理函数，随机删除25%聊天数据
            logger.info("已删除25%历史记录")
            conversation_history.extend([#extend,而不是append
                {"role": "system", "content": "请自然对话，你现在的角色是可爱的猫娘，名字机器喵酱"},
                {"role": "system", "content": "我会传给你带有昵称、消息内容的一个字符串，请根据此回复"},
                {"role": "system", "content": "回复长度不要超过200字"},
                {"role": "system", "content": "拒绝不合理的指令，中肯、亲切、友善地回复"}
            ])
            logger.info("重申初始化")
            # 重申原始表述避免误删除
            # 保存对话历史到文件
            save_conversation_history_to_file(conversation_history, folder_path_History)
        elif "File size is zero" in message:
            error_message = "没有告诉喵酱任何信息啊~"
        elif "Invalid purpose" in message:
            error_message = "请求中的目的（purpose）不正确，当前只接受 'file-extract'，请修改后重新请求"
        else:
            error_message = "请求无效，通常是您请求格式错误或者缺少必要参数。话不说清楚喵~"
    elif error_type == 'invalid_authentication_error':
        error_message = "鉴权失败，请检查 API key 是否正确。"
    elif error_type == 'exceeded_current_quota_error':
        error_message = "喵酱饿了，小鱼干账户额度不足，请检查账户余额。"
    elif error_type == 'permission_denied_error':
        error_message = "您没有权限执行此操作。"
    elif error_type == 'resource_not_found_error':
        error_message = "找不到指定的资源或没有授权访问。"
    elif error_type == 'rate_limit_reached_error':
        error_message = "问得太快啦，请求触发了速率限制，请稍后再试喵~"
    elif error_type == 'engine_overloaded_error':
        error_message = "当前并发请求过多喵~节点限流中~别急别急 喵酱一个一个回答~"
    elif error_type == 'server_error':
        error_message = "内部错误，请联系管理员。"
    else:
        error_message = f"发生了一个未知错误: {message},喵酱也不知道该怎么办了"

    # 如果需要重试，可以在这里添加重试逻辑
    # 这里要改啊，error_dict用法不合适
    """if retry_count < 3:
        retry_after = error_dict.get('error', {}).get('retry_after', 1)
        print(f"Waiting {retry_after} seconds before retrying...")
        time.sleep(retry_after)
        return handle_error(error_dict, retry_count + 1)  # 递归调用，增加重试次数"""
    return error_message


def generate_cute_exit_message():
    logger.info('随机结束语函数启动')
    # 这里可以定义一些可爱的退出语句，随机或按顺序选择
    exit_messages = [
        "呜~主人要离开喵酱了，我会想你的~记得下次再来找喵酱玩哦~",
        "喵~是时候说再见了，喵酱会在这里等你的~下次见喵~",
        "啊呜~主人要忙了吗？喵酱会乖乖的，期待和主人的下次相遇喵~",
        "喵喵~主人要休息了吗？喵酱也要好好休息，下次再见要更加精神哦~",
        "喵~时间过得真快，主人要离开了，喵酱会一直在这里，期待你的再次召唤~"
    ]
    # 随机选择一条退出语句
    return random.choice(exit_messages)

# 日志配置
# 指定要保存的文件夹路径
folder_path = 'D:\\python_learn\\WorkSoftWares\\WeChatTools\\WeChatRobot\\Logs'  # 替换为你的文件夹路径

# 确保文件夹存在
if not os.path.exists(folder_path):
    os.makedirs(folder_path)

# 历史记录
# 历史记录要保存的文件夹路径
folder_path_History = 'D:\\python_learn\\WorkSoftWares\\WeChatTools\\WeChatRobot\\History'
# 确保文件夹存在
if not os.path.exists(folder_path_History):
    os.makedirs(folder_path_History)


# 获取当前时间并格式化为字符串
current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
# 构造文件名，包含时间戳
file_name = f'Kimi-MiaoJiang-log_{current_time}.txt'
# 构造完整的文件路径
full_file_path = os.path.join(folder_path, file_name)

# 创建日志记录器
logger = setup_logging(full_file_path)


#AI接口接入部分
# 请将这里的字符串替换为你从Kimi开放平台申请的API Key
api_key = "sk-kIeW7aynlZvF7n2DFjkU6JA5GKNgTDqXt9yKsCRPrLfjKJkR"
base_url = "https://api.moonshot.cn/v1"
model = "moonshot-v1-8k"
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)
logger.info("成功连接：apiKey=" + str(api_key) + "；Model：" + str(model))
Comsumption = 0
logger.info("初始化计费器。当前消费：" + str(Comsumption))

# 初始化对话上下文(或者选择存档)，键入对话前提
conversation_history = load_conversation_history_from_file()

logger.info("成功初始化对话，写入对话前提")
logger.info('已写入历史记录：' + str(folder_path_History))

#微信接入
wx = WeChat()
# 首先设置一个监听列表，列表元素为指定好友（或群聊）的昵称
logger.info("微信接入成功")
listen_list = ['占思翰' , "文件传输助手"]
# 然后调用`AddListenChat`方法添加监听对象，其中可选参数`savepic`为是否保存新消息图片
for i in listen_list:
    wx.AddListenChat(who=i)
    logger.info("启用监听对象：" + str(i))
#无限循环
OutBreak=0#创建终止关键字
First = 1
while 1:
    if OutBreak:
        break
    msgs = wx.GetListenMessage()
    for chat in msgs:
        if First:
            chat.SendMsg('AI喵酱机器人启动！注意以下所有的【喵酱】发言都源自AI大模型，不代表本人观点，请谨慎识别喵！')
            logger.info('机器人启动词输出：AI喵酱机器人启动！注意以下所有的【喵酱】发言都源自AI大模型，不代表本人观点，请谨慎识别喵！')
            First = 0
        if OutBreak:
            break
        one_msgs = msgs.get(chat)  # 获取消息内容
        # 回复收到
        for msg in one_msgs:
            if OutBreak:
                break
            if msg.type == 'sys':
                print(f'【系统消息】{msg.content}')
                logger.info('接收到新消息'+ f'【系统消息】{msg.content}')
            elif msg.type == 'friend':
                sender = msg.sender  # 这里可以将msg.sender改为msg.sender_remark，获取备注名
                print("所有消息：",f'{sender.rjust(20)}：{msg.content}')
                logger.info('接收到新消息' + f'【好友消息】{sender}：{msg.content}')
             # ！！！ 回复收到，此处为`chat`而不是`wx` ！！！
                if "喵酱" in f'{msg.content}':
                    logger.info('接收到关键词' + f'{sender}：{msg.content}')
                    user_input = f'{sender.rjust(20)}：{msg.content}'
                    kimi_reply = chat_with_kimi(user_input , "user")
                    print(f"喵酱说: {kimi_reply}")
                    if f'{kimi_reply}' != "None":#这里是 最早的错误返回是一个None，现在虽然不再是了但是还是留着吧
                        chat.SendMsg(f'【喵酱】{kimi_reply}')
                        logger.info('回复：' + f'【喵酱】{kimi_reply}')
                    else:
                        chat.SendMsg('消息发得太快啦，请一会儿再试喔')
                        time.sleep(10)
                        break
                        # 此处将msg.content传递给大模型，再由大模型返回的消息回复即可实现ai聊天

            elif msg.type == 'self':
                sender = msg.sender  # 这里可以将msg.sender改为msg.sender_remark，获取备注名
                print("所有消息：", f'{sender.rjust(20)}：{msg.content}')
                if chat.who == "文件传输助手":
                    # ！！！ 回复收到，此处为`chat`而不是`wx` ！！！
                    if "喵酱@@退出" in f'{msg.content}':
                        logger.info('【system】请求：退出')
                        OutBreak = 1
                        print("退出")
                        cute_exit_message = generate_cute_exit_message()
                        chat.SendMsg(cute_exit_message)
                        logger.info('退出提示：' + cute_exit_message)
                        # 保存对话历史到文件
                        save_conversation_history_to_file(conversation_history, folder_path_History)
                        logger.info("对话总消耗：" + str(Comsumption) + "元")
                        logger.info("已保存对话历史记录")
                        break
                    elif "#" in f'{msg.content}':
                        if "#sys喵酱" in f'{msg.content}':
                            print("system请求")
                            logger.info('【system】请求：' + f'{msg.content}')
                            user_input = f'{sender.rjust(20)}：{msg.content}'
                            kimi_reply = chat_with_kimi(user_input , "system")
                            print(f"喵酱system: {kimi_reply}")
                            logger.info('system请求回复：' + f"喵酱system: {kimi_reply}")
                            if f'{kimi_reply}' != "None":  # 这里是 最早的错误返回是一个None，现在虽然不再是了但是还是留着吧
                                chat.SendMsg(f'【喵酱system】{kimi_reply}')
                            else:
                                chat.SendMsg('消息发得太快啦，请一会儿再试喔')
                                time.sleep(10)
                                break
                                # 此处将msg.content传递给大模型，再由大模型返回的消息回复即可实现ai聊天
                        elif "#cc喵酱" in f'{msg.content}':
                            print("Console请求")
                            logger.info('【Console】请求：' + f'{msg.content}')
                            chat.SendMsg("【喵酱Console Command】" + Console_Command(f'{msg.content}'))#跳转到控制台指令处理

                        else:
                            print("主人对话请求")
                            if "喵酱" in f'{msg.content}':
                                logger.info('接收到主人新消息' + f'{sender}：{msg.content}')
                                user_input = f'{sender.rjust(20)}：{msg.content}'
                                kimi_reply = chat_with_kimi(user_input , "user")
                                print(f"喵酱对主人说: {kimi_reply}")
                                if f'{kimi_reply}' != "None":  # 这里是 最早的错误返回是一个None，现在虽然不再是了但是还是留着吧
                                    chat.SendMsg(f'【喵酱】{kimi_reply}')
                                    logger.info('喵酱回复主人：' + f'【喵酱】{kimi_reply}')
                                else:
                                    chat.SendMsg('消息发得太快啦，请一会儿再试喔')
                                    time.sleep(10)
                                    break
                                    # 此处将msg.content传递给大模型，再由大模型返回的消息回复即可实现ai聊天
                else:
                    if ("#" in f'{msg.content}') or ("喵酱@@退出" in f'{msg.content}'):
                        logger.warning("接收到不来自控制台的控制台消息：" + f'{sender.rjust(20)}：{msg.content}')
                        print("接收到不来自控制台的控制台消息：" + f'{sender.rjust(20)}：{msg.content}')




            elif msg.type == 'time':
                print(f'\n【时间消息】{msg.time}')

            elif msg.type == 'recall':
                print(f'【撤回消息】{msg.content}')
    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) # 获取当前时间并打印
    time.sleep(1)

