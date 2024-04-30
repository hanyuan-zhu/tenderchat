// 创建一个新的 Date 当日日期对象
var now = new Date();
// 将 Date 对象转换为北京时间的日期字符串
var dateString = now.toLocaleDateString("zh-CN", { timeZone: "Asia/Shanghai" });
// 获取当前时间
var currentTime = new Date().toLocaleTimeString();
var tabElement = document.querySelector(".date");
tabElement.textContent = dateString;

function sendMessage() {
    var input = document.getElementById('chat-input').value; // 获取用户输入
    var chatBox = document.getElementById('chat-box'); // 获取显示对话的容器

    // 如果用户输入为空或者只包含空格，那么直接返回
    if (!input.trim()) {
        return false;
    }

    // 用户消息头部
    var userHeaderDiv = document.createElement("div");
    userHeaderDiv.className = 'message-header-right';
    userHeaderDiv.textContent = `You, ${currentTime}`;
    chatBox.appendChild(userHeaderDiv);

    // 显示用户输入到界面
    var userDiv = document.createElement("div");
    userDiv.className = 'user-message';
    userDiv.textContent = input;
    chatBox.appendChild(userDiv);

    // 准备发送到服务器
    fetch('/query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ input: input })
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
             // 将换行符转换为HTML的<br>标签
             let formattedText = data.result.replace(/\n/g, '<br>');
             // 将文本中的**text**转换为加粗
             formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            
            // AI消息头部
            var aiHeaderDiv = document.createElement("div");
            aiHeaderDiv.className = 'message-header-left';
            aiHeaderDiv.innerHTML = `AI, ${currentTime}`;
            chatBox.appendChild(aiHeaderDiv);

            // 显示AI的回答
            var aiDiv = document.createElement("div");
            aiDiv.className = 'ai-message';
            aiDiv.innerHTML = formattedText;
            chatBox.appendChild(aiDiv);
            // 滚动到最新消息
            setTimeout(() => {
                chatBox.scrollTop = chatBox.scrollHeight;
            }, 0);

        })
        .catch(error => {
            console.error('Error:', error);
            var errorDiv = document.createElement("div");
            errorDiv.textContent = "Error: " + error;
            chatBox.appendChild(errorDiv);
        });

    // 清空输入框
    document.getElementById('chat-input').value = '';
    return false;  // 阻止表单默认提交
}

// 处理 'logs' 事件：
// 处理 'logs' WebSocket 事件：
var ws = new WebSocket('ws://localhost:5001/logs');

ws.onopen = function () {
    console.log('WebSocket connection opened');
};

ws.onmessage = function (event) {
    console.log('Received logger: ', event.data);
    var workspace = document.getElementById('Workspace');
    if (workspace) {
        workspace.innerHTML += event.data + '<br>';
        setTimeout(() => {
            workspace.scrollTop = workspace.scrollHeight;
        }, 0);
        console.log('Log appended to workspace.');
    } else {
        console.error('Workspace element not found.');
    }
};

ws.onerror = function (event) {
    console.error('WebSocket error: ', event);
};

ws.onclose = function () {
    console.log('WebSocket connection closed');
};

function openTab(evt, tabName) {
    var i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tab-content");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
        tabcontent[i].className = tabcontent[i].className.replace(" active", "");
    }

    tablinks = document.getElementsByClassName("tab");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }

    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
    document.getElementById(tabName).className += " active";
}
window.onload = function () {
    document.querySelector('.tabs .tab').click();
};

