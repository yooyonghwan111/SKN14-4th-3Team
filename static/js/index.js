// 전역 변수
let conversations = {
  1: {
    title: "대화 1",
    messages: [
      {
        role: "system",
        content: "세탁기/건조기 매뉴얼 Q&A 챗봇이 시작되었습니다.",
      },
    ],
    image: null,
  },
};
let currentConversationId = "1";
let isTyping = false;

// DOM 요소
const chatMessages = document.getElementById("chatMessages");
const messageInput = document.getElementById("messageInput");
const chatForm = document.getElementById("chatForm");
const imageInput = document.getElementById("imageInput");
const imageUploadArea = document.getElementById("imageUploadArea");
const imageDisplayArea = document.getElementById("imageDisplayArea");
const conversationList = document.getElementById("conversationList");
const newChatBtn = document.getElementById("newChatBtn");
const clearAllBtn = document.getElementById("clearAllBtn");
const clearCurrBtn = document.getElementById("clearCurrBtn");
const downloadBtn = document.getElementById("downloadBtn");
const downloadCurrBtn = document.getElementById("downloadCurrBtn");
const totalMessages = document.getElementById("totalMessages");
const totalConversations = document.getElementById("totalConversations");

// 초기화
document.addEventListener("DOMContentLoaded", function () {
  updateChatDisplay();
  updateStats();
  setupEventListeners();
});

// 이벤트 리스너 설정
function setupEventListeners() {
  // 채팅 폼 제출
  chatForm.addEventListener("submit", handleChatSubmit);

  // 이미지 업로드
  imageUploadArea.addEventListener("click", () => imageInput.click());
  imageInput.addEventListener("change", handleImageUpload);

  // 드래그 앤 드롭
  imageUploadArea.addEventListener("dragover", handleDragOver);
  imageUploadArea.addEventListener("drop", handleDrop);
  imageUploadArea.addEventListener("dragleave", handleDragLeave);

  // 버튼 이벤트
  newChatBtn.addEventListener("click", createNewConversation);
  clearAllBtn.addEventListener("click", clearAllConversations);
  clearCurrBtn.addEventListener("click", clearCurrConversations);
  downloadBtn.addEventListener("click", downloadChatHistory);
  downloadCurrBtn.addEventListener("click", downloadChatCurrHistory);
}

// 채팅 제출 처리
async function handleChatSubmit(e) {
  e.preventDefault();
  const message = messageInput.value.trim();
  const OriginConvId = currentConversationId;  // 요청 시점의 대화 ID 복사
  const currentConv = conversations[OriginConvId];

  if (!message && !currentConv.image) return;

  if (message) {
    addMessage("user", message);
    messageInput.value = "";
  }

  // 서버 연동
  const history = currentConv.messages
    .filter((m) => m.role !== "system")
    .map((m) => ({ role: m.role, content: m.content }));

  showTypingIndicator();
  try {
    const response = await sendChatQuery(message, history);
    console.log("서버 응답:", response);
    hideTypingIndicator();

    const reply = response.response || "응답을 불러오지 못했습니다.";

    // 응답 도착 시 현재 대화방 확인
    if (OriginConvId === currentConversationId) {
      addMessage("assistant", reply);
    } else {
      // 대화방이 바뀐 경우에도 원래 대화방에 응답 메시지 추가
      conversations[OriginConvId].messages.push({
        role: "assistant",
        content: reply,
        timestamp: new Date(),
      });

      console.warn("응답이 도착했지만 대화방이 바뀌어 해당 방에만 저장되었습니다.");
    }

    updateStats();
  } catch (error) {
    hideTypingIndicator();
    const errorMsg = "서버 오류가 발생했습니다.";

    if (OriginConvId === currentConversationId) {
      addMessage("assistant", errorMsg);
    } else {
      conversations[OriginConvId].messages.push({
        role: "assistant",
        content: errorMsg,
        timestamp: new Date(),
      });
    }

    console.error("Chat API error:", error);
  }
}



// 메시지 추가
function addMessage(role, content) {
  conversations[currentConversationId].messages.push({
    role: role,
    content: content,
    timestamp: new Date(),
  });
  updateChatDisplay();
  updateStats();
  scrollToBottom();
}

// 타이핑 인디케이터
function showTypingIndicator() {
  const typingDiv = document.createElement("div");
  typingDiv.className = "message bot typing-message";
  typingDiv.innerHTML = `
                <div class="avatar bot">🤖</div>
                <div class="message-content">
                    <div class="typing-indicator">
                        답변을 작성 중입니다<span class="typing-dots"></span>
                    </div>
                </div>
            `;
  chatMessages.appendChild(typingDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTypingIndicator() {
  const typingMessage = chatMessages.querySelector(".typing-message");
  if (typingMessage) {
    typingMessage.remove();
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatMessageContent(content) {
  // HTML 이스케이프 먼저 수행 (보안상 안전하게)
  const escaped = escapeHtml(content);

  // # 헤더 스타일 변환 (간단히 한 줄만 h1 처리)
  const lines = escaped.split("\n").map(line => {
    if (line.startsWith("### ")) return `<h3>${line.slice(4)}</h3>`;
    if (line.startsWith("## ")) return `<h2>${line.slice(3)}</h2>`;
    if (line.startsWith("# ")) return `<h1>${line.slice(2)}</h1>`;
    return line;
  });

  // 줄바꿈 처리
  return lines.join("<br>");
}

// 채팅 화면 업데이트
function updateChatDisplay() {
  const messages = conversations[currentConversationId].messages;
  chatMessages.innerHTML = "";

  messages.forEach((message) => {
    const messageDiv = document.createElement("div");

    if (message.role === "system") {
      messageDiv.className = "system-message";
      messageDiv.innerHTML = `${escapeHtml(message.content)}`;
    } else {
      messageDiv.className = `message ${message.role}`;
      const avatar = message.role === "user" ? "👤" : "🤖";
      const avatarClass = message.role === "user" ? "user" : "bot";

      const formattedContent = formatMessageContent(message.content);

      messageDiv.innerHTML = `
        ${message.role === "user" ? "" : `<div class="avatar ${avatarClass}">${avatar}</div>`}
        <div class="message-content">${formattedContent}</div>
        ${message.role === "user" ? `<div class="avatar ${avatarClass}">${avatar}</div>` : ""}
      `;
    }

    chatMessages.appendChild(messageDiv);
  });

  chatMessages.scrollTop = chatMessages.scrollHeight;
  updateImageDisplay();
}

// 이미지 업로드 처리
function handleImageUpload(e) {
  const file = e.target.files[0];
  if (file) {
    processImage(file);
  }
}

// 이미지 처리
function processImage(file) {
  const reader = new FileReader();
  reader.onload = async function (e) {
    conversations[currentConversationId].image = {
      src: e.target.result,
      name: file.name,
    };
    updateImageDisplay();
    addMessage("user", "이미지를 업로드했습니다.");

    try {
      const result = await uploadImageAndGetModelCode(file);
      const modelInfo = result.model || "모델 정보를 찾을 수 없습니다.";
      addMessage("assistant", `이미지 분석 결과: ${modelInfo}`);
    } catch (err) {
      console.error("Image upload error:", err);
      addMessage("assistant", "이미지 분석 중 오류가 발생했습니다.");
    }
  };
  reader.readAsDataURL(file);
}


// 이미지 표시 업데이트
function updateImageDisplay() {
  const currentImage = conversations[currentConversationId].image;

  if (currentImage) {
    imageDisplayArea.innerHTML = `
                    <img src="${currentImage.src}" alt="업로드된 이미지" class="uploaded-image">
                    <div class="product-info">
                        <h6>제품명: 분석 중...</h6>
                        <h6>모델명: 확인 중...</h6>
                    </div>
                `;
  } else {
    imageDisplayArea.innerHTML = `
                    <div class="text-center text-muted">
                        <p>현재 대화에 업로드된 이미지가 없습니다.</p>
                    </div>
                `;
  }
}

// 드래그 앤 드롭 처리
function handleDragOver(e) {
  e.preventDefault();
  imageUploadArea.classList.add("dragover");
}

function handleDrop(e) {
  e.preventDefault();
  imageUploadArea.classList.remove("dragover");
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    processImage(files[0]);
  }
}

function handleDragLeave(e) {
  imageUploadArea.classList.remove("dragover");
}

// 새 대화 생성
function createNewConversation() {
  const newId = String(
    Math.max(...Object.keys(conversations).map((k) => parseInt(k))) + 1
  );
  conversations[newId] = {
    title: `대화 ${newId}`,
    messages: [
      {
        role: "system",
        content: "세탁기/건조기 매뉴얼 Q&A 챗봇이 시작되었습니다.",
      },
    ],
    image: null,
  };
  currentConversationId = newId;
  updateConversationList();
  updateChatDisplay();
  updateStats();
}

// 대화 목록 업데이트
function updateConversationList() {
  conversationList.innerHTML = "";
  Object.keys(conversations).forEach((id) => {
    const button = document.createElement("button");
    button.className = `btn conversation-item w-100 ${
      id === currentConversationId ? "active" : ""
    }`;
    button.setAttribute("data-id", id);
    button.innerHTML = `${conversations[id].title}`;
    button.addEventListener("click", () => switchConversation(id));
    conversationList.appendChild(button);
  });
}

// 대화 전환
function switchConversation(id) {
  currentConversationId = id;
  updateConversationList();
  updateChatDisplay();
}

// 모든 대화 삭제
function clearAllConversations() {
  if (confirm("정말로 모든 대화 기록을 삭제하시겠습니까?")) {
    conversations = {
      1: {
        title: "대화 1",
        messages: [
          {
            role: "system",
            content: "세탁기/건조기 매뉴얼 Q&A 챗봇이 시작되었습니다.",
          },
        ],
        image: null,
      },
    };
    currentConversationId = "1";
    updateConversationList();
    updateChatDisplay();
    updateStats();
  }
}

// 현재 대화 삭제 (해당 대화만 초기화)
function clearCurrConversations() {
  if (confirm("정말로 현재 대화 기록을 삭제하시겠습니까?")) {
    if (conversations[currentConversationId]) {
      conversations[currentConversationId] = {
        title: `대화 ${currentConversationId}`,
        messages: [
          {
            role: "system",
            content: "세탁기/건조기 매뉴얼 Q&A 챗봇이 시작되었습니다.",
          },
        ],
        image: null,
      };
      updateChatDisplay();
      updateStats();
    } else {
      alert("현재 대화를 찾을 수 없습니다.");
    }
  }
}

// 채팅 기록 다운로드
function downloadChatHistory() {
  const data = {
    conversations: conversations,
    downloadDate: new Date().toISOString(),
  };
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `chat_history_${new Date()
    .toISOString()
    .slice(0, 19)
    .replace(/:/g, "-")}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

// 현재 대화 기록만 다운로드
function downloadChatCurrHistory() {
  const currConv = conversations[currentConversationId];
  if (!currConv) {
    alert("현재 대화 기록이 없습니다.");
    return;
  }

  const data = {
    title: currConv.title,
    messages: currConv.messages,
    image: currConv.image,
    downloadDate: new Date().toISOString(),
  };

  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `chat_${currentConversationId}_${new Date()
    .toISOString()
    .slice(0, 19)
    .replace(/:/g, "-")}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

// 통계 업데이트
function updateStats() {
  const totalMsg = Object.values(conversations).reduce(
    (total, conv) =>
      total + conv.messages.filter((m) => m.role !== "system").length,
    0
  );
  totalMessages.textContent = totalMsg;
  totalConversations.textContent = Object.keys(conversations).length;
}

function scrollToBottom() {
  const chatBox = document.getElementById("chatMessages");
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendChatQuery(query, history=[]) {
  const response = await fetch('/api/chat/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, history })
  });
  return await response.json();
}

async function uploadImageAndGetModelCode(imageFile) {
  const formData = new FormData();
  formData.append("image", imageFile);

  const response = await fetch('/api/model-search/', {
    method: 'POST',
    body: formData
  });
  return await response.json();
}