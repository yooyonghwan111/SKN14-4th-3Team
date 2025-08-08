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
let isAuthenticated = false;

// DOM 요소 (안전하게 가져오기)
let chatMessages, messageInput, chatForm, imageInput, imageDisplayArea;
let conversationList, newChatBtn, clearAllBtn, deleteCurrBtn, downloadBtn, downloadCurrBtn;
let totalMessages, totalConversations;

function getDOMElements() {
  chatMessages = document.getElementById("chatMessages");
  messageInput = document.getElementById("messageInput");
  chatForm = document.getElementById("chatForm");
  imageInput = document.getElementById("imageInput");
  imageDisplayArea = document.getElementById("imageDisplayArea");
  conversationList = document.getElementById("conversationList");
  newChatBtn = document.getElementById("newChatBtn");
  clearAllBtn = document.getElementById("clearAllBtn");
  deleteCurrBtn = document.getElementById("deleteCurrBtn");
  downloadBtn = document.getElementById("downloadBtn");
  downloadCurrBtn = document.getElementById("downloadCurrBtn");
  totalMessages = document.getElementById("totalMessages");
  totalConversations = document.getElementById("totalConversations");
}

// 초기화
document.addEventListener("DOMContentLoaded", function () {
  // DOM 요소들 가져오기
  getDOMElements();
  
  // 로그인 상태 확인
  isAuthenticated = document.querySelector('.conversation-list') !== null;
  
  if (isAuthenticated) {
    loadUserConversations();
    setupEventListeners();
  } else {
    // 로그인하지 않은 경우 기본 이벤트만 설정
    setupBasicEventListeners();
  }
});

// 사용자 대화 목록 로드
async function loadUserConversations() {
  try {
    const response = await fetch('/api/conversations/', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      conversations = {};
      
      if (data.conversations && data.conversations.length > 0) {
        // 기존 대화들을 로드
        for (const conv of data.conversations) {
          conversations[conv.id] = {
            id: conv.id,
            title: conv.title,
            messages: [
              {
                role: "system",
                content: "세탁기/건조기 매뉴얼 Q&A 챗봇이 시작되었습니다.",
              },
            ],
            image: null,
          };
        }
        currentConversationId = data.conversations[0].id.toString();
        
        // 첫 번째 대화의 메시지들 로드
        await loadConversationMessages(currentConversationId);
      } else {
        // 대화가 없으면 새 대화 생성
        await createNewConversation();
      }
    } else {
      console.error('Failed to load conversations');
      setupDefaultConversation();
    }
  } catch (error) {
    console.error('Error loading conversations:', error);
    setupDefaultConversation();
  }
  
  updateConversationList();
  updateChatDisplay();
  updateStats();
}

// 특정 대화의 메시지들 로드
async function loadConversationMessages(conversationId) {
  try {
    const response = await fetch(`/api/conversations/${conversationId}/messages/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      conversations[conversationId].messages = [
        {
          role: "system",
          content: "세탁기/건조기 매뉴얼 Q&A 챗봇이 시작되었습니다.",
        },
        ...data.messages
      ];
    }
  } catch (error) {
    console.error('Error loading messages:', error);
  }
}

// 기본 대화 설정
function setupDefaultConversation() {
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
}

// 기본 이벤트 리스너 설정 (로그인하지 않은 경우)
function setupBasicEventListeners() {
  // 로그인하지 않은 경우 기본 대화 설정
  if (!conversations) {
    setupDefaultConversation();
  }
  
  // 채팅 폼 처리
  if (chatForm) {
    chatForm.addEventListener("submit", handleChatSubmit);
  }
  
  // 이미지 업로드 처리
  if (imageInput) {
    imageInput.addEventListener("change", handleImageUpload);
  }
  
  // 클립 아이콘 클릭 시 파일 입력 트리거
  const clipIcon = document.querySelector('label[for="imageInput"]');
  if (clipIcon) {
    clipIcon.addEventListener("click", function(e) {
      e.preventDefault();
      imageInput.click();
    });
  }
  
  // 기본 채팅 화면 업데이트
  updateChatDisplay();
}

// 이벤트 리스너 설정
function setupEventListeners() {
  // 채팅 폼 제출
  if (chatForm) {
    chatForm.addEventListener("submit", handleChatSubmit);
  }

  // 이미지 업로드
  if (imageInput) {
    imageInput.addEventListener("change", handleImageUpload);
  }
  
  // 클립 아이콘 클릭 시 파일 입력 트리거
  const clipIcon = document.querySelector('label[for="imageInput"]');
  if (clipIcon) {
    clipIcon.addEventListener("click", function(e) {
      e.preventDefault();
      imageInput.click();
    });
  }

  // 버튼 이벤트
  if (newChatBtn) {
    newChatBtn.addEventListener("click", createNewConversation);
  }
  if (clearAllBtn) {
    clearAllBtn.addEventListener("click", clearAllConversations);
  }
  if (deleteCurrBtn) {
    deleteCurrBtn.addEventListener("click", deleteCurrentConversation);
  }
  if (downloadBtn) {
    downloadBtn.addEventListener("click", downloadChatHistory);
  }
  if (downloadCurrBtn) {
    downloadCurrBtn.addEventListener("click", downloadChatCurrHistory);
  }
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

  if (isAuthenticated) {
    // 로그인한 사용자는 서버에 메시지 저장
    await sendMessageToServer(OriginConvId, message);
  } else {
    // 로그인하지 않은 사용자는 기존 방식 사용
    const history = currentConv.messages
      .filter((m) => m.role !== "system")
      .map((m) => ({ role: m.role, content: m.content }));

    showTypingIndicator();
    try {
      const response = await sendChatQuery(message, history);
      hideTypingIndicator();

      const reply = response.response || "응답을 불러오지 못했습니다.";

      if (OriginConvId === currentConversationId) {
        addMessage("assistant", reply);
      } else {
        conversations[OriginConvId].messages.push({
          role: "assistant",
          content: reply,
          timestamp: new Date(),
        });
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
}

// 서버에 메시지 전송 (로그인한 사용자용)
async function sendMessageToServer(conversationId, message) {
  showTypingIndicator();
  
  try {
    const response = await fetch(`/api/conversations/${conversationId}/messages/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message: message })
    });
    
    if (response.ok) {
      const data = await response.json();
      hideTypingIndicator();
      
      // 사용자 메시지와 챗봇 응답을 화면에 추가
      if (conversationId === currentConversationId) {
        // 대화 제목 업데이트
        if (data.user_message && data.assistant_message) {
          conversations[conversationId].title = message.substring(0, 50) + (message.length > 50 ? "..." : "");
          updateConversationList();
        }
        
        // 챗봇 응답만 추가 (사용자 메시지는 이미 추가됨)
        if (data.assistant_message) {
          addMessage("assistant", data.assistant_message.content);
        }
      }
      
      updateStats();
    } else {
      throw new Error('Failed to send message');
    }
  } catch (error) {
    hideTypingIndicator();
    const errorMsg = "서버 오류가 발생했습니다.";
    
    if (conversationId === currentConversationId) {
      addMessage("assistant", errorMsg);
    }
    
    console.error("Message API error:", error);
  }
}

// 메시지 추가
function addMessage(role, content) {
  if (!conversations[currentConversationId]) return;
  
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
  if (!chatMessages || !conversations[currentConversationId]) return;
  
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
    // 이미지 정보를 대화에 저장
    conversations[currentConversationId].image = {
      src: e.target.result,
      name: file.name,
    };
    
    // 즉시 이미지 표시 업데이트
    updateImageDisplay();
    
    // 사용자 메시지 추가
    addMessage("user", `이미지를 업로드했습니다: ${file.name}`);

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
  if (!imageDisplayArea || !conversations[currentConversationId]) return;
  
  const currentImage = conversations[currentConversationId].image;

  if (currentImage) {
    imageDisplayArea.innerHTML = `
      <div class="uploaded-image-container">
        <img src="${currentImage.src}" alt="업로드된 이미지" class="uploaded-image">
        <div class="product-info">
          <h6>제품명: 분석 중...</h6>
          <h6>모델명: 확인 중...</h6>
          <small class="text-muted">파일명: ${currentImage.name}</small>
        </div>
      </div>
    `;
  } else {
    imageDisplayArea.innerHTML = `
      <div class="text-center text-muted">
        <p>현재 대화에 업로드된 이미지가 없습니다.</p>
        <small>이미지를 업로드하면 여기에 표시됩니다.</small>
      </div>
    `;
  }
}

// 새 대화 생성
async function createNewConversation() {
  if (isAuthenticated) {
    // 로그인한 사용자는 서버에 새 대화 생성
    try {
      const response = await fetch('/api/conversations/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ title: "새 대화" })
      });
      
      if (response.ok) {
        const data = await response.json();
        const newId = data.id.toString();
        
        conversations[newId] = {
          id: data.id,
          title: data.title,
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
    } catch (error) {
      console.error('Error creating conversation:', error);
    }
  } else {
    // 로그인하지 않은 사용자는 기존 방식 사용
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
}

// 대화 목록 업데이트
function updateConversationList() {
  if (!conversationList) return;
  
  conversationList.innerHTML = "";
  Object.keys(conversations).forEach((id) => {
    const wrapper = document.createElement("div");
    wrapper.className = `conversation-item-wrapper mb-2 ${
      id === currentConversationId ? "active" : ""
    }`;
    wrapper.setAttribute("data-id", id);
    
    wrapper.innerHTML = `
      <div class="conversation-item d-flex align-items-center p-2">
        <div class="conversation-avatar me-3">
          <i class="bi bi-person-circle"></i>
        </div>
        <div class="conversation-content flex-grow-1" style="cursor: pointer;">
          <div class="conversation-title">${conversations[id].title}</div>
          <div class="conversation-subtitle">세탁기/건조기 매뉴얼 Q&A</div>
        </div>
        <div class="conversation-actions d-flex align-items-center">
          <button class="btn btn-sm btn-outline-danger delete-conversation-btn me-2" 
                  data-id="${id}" 
                  title="대화 삭제"
                  style="padding: 2px 6px; font-size: 12px;">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </div>
    `;
    
    // 대화 선택 이벤트 (제목 부분 클릭)
    const contentArea = wrapper.querySelector('.conversation-content');
    contentArea.addEventListener("click", () => switchConversation(id));
    
    // 삭제 버튼 이벤트
    const deleteBtn = wrapper.querySelector('.delete-conversation-btn');
    deleteBtn.addEventListener("click", (e) => {
      e.stopPropagation(); // 이벤트 버블링 방지
      deleteSpecificConversation(id);
    });
    
    conversationList.appendChild(wrapper);
  });
}

// 대화 전환
async function switchConversation(id) {
  currentConversationId = id;
  
  if (isAuthenticated) {
    // 로그인한 사용자는 서버에서 메시지 로드
    await loadConversationMessages(id);
  }
  
  updateConversationList();
  updateChatDisplay();
}

// 모든 대화 삭제
async function clearAllConversations() {
  if (confirm("정말로 모든 대화 기록을 삭제하시겠습니까?")) {
    if (isAuthenticated) {
      // 로그인한 사용자는 서버에서 대화들 삭제
      try {
        for (const id of Object.keys(conversations)) {
          await fetch(`/api/conversations/${id}/`, {
            method: 'DELETE',
            headers: {
              'Content-Type': 'application/json',
            }
          });
        }
      } catch (error) {
        console.error('Error deleting conversations:', error);
      }
    }
    
    // 새 대화 생성
    await createNewConversation();
  }
}

// 현재 대화 삭제
async function deleteCurrentConversation() {
  if (confirm("정말로 현재 대화를 삭제하시겠습니까?")) {
    await deleteSpecificConversation(currentConversationId);
  }
}

// 특정 대화 삭제
async function deleteSpecificConversation(conversationId) {
  if (confirm("정말로 이 대화를 삭제하시겠습니까?")) {
    if (isAuthenticated) {
      // 로그인한 사용자는 서버에서 대화 삭제
      try {
        const response = await fetch(`/api/conversations/${conversationId}/`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          }
        });
        
        if (!response.ok) {
          throw new Error('서버에서 대화 삭제에 실패했습니다.');
        }
      } catch (error) {
        console.error('Error deleting conversation:', error);
        alert('대화 삭제 중 오류가 발생했습니다.');
        return;
      }
    }
    
    // 로컬에서 대화를 삭제
    delete conversations[conversationId];

    // 삭제된 대화가 현재 대화였다면 다른 대화로 전환
    if (conversationId === currentConversationId) {
      const remainingIds = Object.keys(conversations);
      if (remainingIds.length > 0) {
        // 가장 ID가 낮은 대화로 이동
        currentConversationId = remainingIds.sort((a, b) => parseInt(a) - parseInt(b))[0];
      } else {
        // 남은 대화가 없으면 새 대화 생성
        await createNewConversation();
        return;
      }
    }

    updateConversationList();
    updateChatDisplay();
    updateStats();
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
  if (!totalMessages || !totalConversations) return;
  
  const totalMsg = Object.values(conversations).reduce(
    (total, conv) =>
      total + conv.messages.filter((m) => m.role !== "system").length,
    0
  );
  totalMessages.textContent = totalMsg;
  totalConversations.textContent = Object.keys(conversations).length;
}

function scrollToBottom() {
  if (!chatMessages) return;
  chatMessages.scrollTop = chatMessages.scrollHeight;
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