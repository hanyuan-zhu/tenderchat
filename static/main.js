function toggleTheme() {
    document.body.classList.toggle('theme-dark');
}

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

            // 检查AI回复是否包含特定文字，并根据条件显示或隐藏文件预览窗口
            if (formattedText.includes("请查阅右侧参考文档")) {
                document.getElementById("file-container").style.display = "block";
            } else {
                document.getElementById("file-container").style.display = "none";
            }

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

document.getElementById('arrow-icon-left').addEventListener('click', function() {

    const container = document.querySelector('.agent-container');
    container.classList.toggle('collapsed');
    const workspace = document.getElementById('Workspace');
    if (container.classList.contains('collapsed')) {
        workspace.style.display = 'none';
    } else {
        workspace.style.display = 'block';
    }
});
document.getElementById('arrow-icon-right').addEventListener('click', function() {

    const container = document.querySelector('.file-container');
    container.classList.toggle('collapsed');

    const filezone = document.getElementById('file-zone');
    const webzone = document.getElementById('web-links');
    const searchinput = document.getElementById('search-input');
    if (container.classList.contains('collapsed')) {
        filezone.style.display = 'none';
        webzone.style.display = 'none';
        searchinput.style.display = 'none';
    } else {
        filezone.style.display = 'block';
        webzone.style.display = 'block';
        searchinput.style.display = 'block';
    }
});

// document.addEventListener('DOMContentLoaded', function() {
//     fetch('/file')
//         .then(response => response.json())
//         .then(data => {
//             const announcementList = document.getElementById('announcement-list');
//             data.forEach(item => {
//                 const div = document.createElement('div');
//                 div.classList.add('announcement-item');
//                 div.innerHTML = `
//                     <div class="icon">📄</div>
//                     <div class="details">${item.name}</div>
//                     <div class="actions">
//                         <a href="${item.link}" target="_blank">查看</a>
//                         <a href="${item.download_link}" download>下载</a>
//                     </div>
//                 `;
//                 announcementList.appendChild(div);
//             });
//         });

//     fetch('/web')
//         .then(response => response.json())
//         .then(data => {
//             const webList = document.getElementById('web-list');
//             data.forEach(item => {
//                 const div = document.createElement('div');
//                 div.classList.add('web-item');
//                 div.innerHTML = `
//                     <div class="icon">🌐</div>
//                     <div class="details">${item.name}</div>
//                     <div class="actions">
//                         <a href="${item.link}" target="_blank">查看</a>
//                     </div>
//                 `;
//                 webList.appendChild(div);
//             });
//         });
// });
// 假数据：
document.addEventListener('DOMContentLoaded', function() {
    
    // 假数据
    const fileData = [
        // {
        //     name: "华润水泥（罗定）有限公司2024年6月-罗定水泥-六价铬（VI）测定仪（固定资产）-公开询比价询价结果公告",
        //     link: "https://www.baidu.com/",
        //     download_link: "#"
        // },
        // {
        //     name: "华润水泥（罗定）有限公司2024年7月-罗定水泥-氮氧化物测定仪（固定资产）-公开询比价询价结果公告",
        //     link: "#",
        //     download_link: "#"
        // },
        {
            name: "员工手册.pdf",
            link: "https://www.baidu.com/",
            download_link: "#"
        },
        {
            name: "新员工入职流程.docx",
            link: "#",
            download_link: "#"
        }
    ];

    const webData = [
        // {
        //     name: "华润水泥（罗定）有限公司2024年6月-罗定水泥-六价铬（VI）测定仪（固定资产）-公开询比价询价结果公告",
        //     link: "https://www.baidu.com/"
        // },
        // {
        //     name: "华润水泥（罗定）有限公司2024年6月-罗定水泥-六价铬（VI）测定仪（固定资产）-公开询比价询价结果公告",
        //     link: "#"
        // },
        {
            name:"荔湾区葵蓬南住房项目基坑支护工程设计施工总承包SL202404300060",
            link:"https://www.ggzy.gov.cn/information/html/a/440000/0105/202405/01/00449da3b9d0609c437cb52ba430784bfc5d.shtml"
        },
        {
            name:"荔湾区公安分局档案中心大楼改造工程",
            link:"https://ygp.gdzwfw.gov.cn/ggzy-portal/#/44/new/jygg/v3/A?noticeId=eeaa02ca-685d-40c9-b68e-cf05f4aa263a&projectCode=E4401000002401274001&bizCode=3C52&siteCode=440100&publishDate=20240430020018&source=%E5%B9%BF%E4%BA%A4%E6%98%93%E6%95%B0%E5%AD%97%E4%BA%A4%E6%98%93%E5%B9%B3%E5%8F%B0&titleDetails=%E5%B7%A5%E7%A8%8B%E5%BB%BA%E8%AE%BE"
        },
        {
            name:"荔湾区委党校建设工程勘察设计",
            link:"https://www.ggzy.gov.cn/information/html/a/440000/0102/202404/29/0044a73477d2875d43eaa9f4fb5db2cf868c.shtml"
        }
    ];

    // 渲染文件数据
    const announcementList = document.getElementById('file-zone-item-list');
    fileData.forEach(item => {
        const div = document.createElement('div');
        div.classList.add('file-zone-item');
        div.innerHTML = `
            <div class="file-zone-big-icon">📄</div>
            <div class="file-name">${item.name}</div>
            <div class="file-actions">
                <a href="${item.link}" target="_blank" class="view-button"><img src="${eyeIconUrl}" alt="查看"></a>
                <a href="${item.download_link}" download><img src="${downloadIconUrl}" alt="下载"></a>
            </div>
        `;
        announcementList.appendChild(div);
    });

    // 渲染网页数据
    const webList = document.getElementById('web-list');
    
    webData.forEach(item => {
        const div = document.createElement('div');
        div.classList.add('web-item');
        div.innerHTML = `
            <div class="file-zone-big-icon">🔗</div>
            <div class="file-name">${item.name}</div>
            <div class="file-actions">
                <a href="${item.link}" target="_blank" class="view-button"><img src="${eyeIconUrl}" alt="查看"></a>
                <a href="${item.link}" target="_blank"><img src="${browserIconUrl}" alt="浏览器中打开"></a>
            </div>
        `;
        webList.appendChild(div);
    });

    document.querySelectorAll('.view-button').forEach(button => {
    button.addEventListener('click', event => {
        event.preventDefault();
        document.getElementById('iframe').src = event.currentTarget.href;
        document.getElementById('iframe-container').style.display = 'block';

        // 隐藏元素
        document.querySelectorAll('.file-header, .file-zone, .web-links').forEach(element => {
            element.style.display = 'none';
        });
    });
});

document.getElementById('back-button').addEventListener('click', () => {
    document.getElementById('iframe-container').style.display = 'none';

    // 显示元素
    document.querySelectorAll('.file-header, .file-zone, .web-links').forEach(element => {
        element.style.display = '';
    });
});
});


