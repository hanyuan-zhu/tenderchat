// 创建一个新的 Date 当日日期对象
var now = new Date();
// 将 Date 对象转换为北京时间的日期字符串
var dateString = now.toLocaleDateString("zh-CN", { timeZone: "Asia/Shanghai" });
var tabElement = document.querySelector(".date");
tabElement.textContent = dateString;

function sendMessage() {
    var input = document.getElementById('chat-input').value; // 获取用户输入
    var chatBox = document.getElementById('chat-box'); // 获取显示对话的容器

    // 如果用户输入为空或者只包含空格，那么直接返回
    if (!input.trim()) {
        return false;
    }
    // 显示用户输入到界面
    var userDiv = document.createElement("div");
    userDiv.textContent = "You: " + input;
    userDiv.className = 'user-message'; // 应用用户消息的CSS类
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
            // 显示AI的回答
            var aiDiv = document.createElement("div");
            aiDiv.className = 'ai-message'; // 应用AI消息的CSS类
            // aiDiv.textContent = "AI: " + data.result;  // 修改这里：使用 data.result 而不是 data.result.output
            var formattedData = data.result
                .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>') // replaces markdown bold syntax with HTML bold tags
            aiDiv.innerHTML =  "AI: "+formattedData;
        
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
    console.log('Received message: ', event.data);

    var workspace = document.getElementById('Workspace');
    if (workspace) {
        workspace.innerHTML += event.data + '<br>';
        setTimeout(() => {
            workspace.scrollTop = workspace.scrollHeight;
        }, 3000);
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

