// Configuration
// Import configuration from config.js
const API_ENDPOINT = config.API_ENDPOINT;
const AWS_REGION = config.AWS_REGION;
const COGNITO_APP_CLIENT_ID = config.COGNITO_APP_CLIENT_ID;
const REDIRECT_URI = config.REDIRECT_URI;
const COGNITO_DOMAIN = config.COGNITO_DOMAIN;


// DOM elements
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const chatToggle = document.getElementById('chatToggle');
const chatPopup = document.getElementById('chatPopup');
const closeBtn = document.getElementById('closeBtn');

document.cookie = `sessionId=${"default"}; path=/; secure; samesite=strict`;

// Event listeners
sendButton.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Chat popup toggle functionality
chatToggle.addEventListener('click', () => {
    chatPopup.classList.toggle('show');
});

closeBtn.addEventListener('click', () => {
    chatPopup.classList.remove('show');
});

// Send message function
async function sendMessage() {
    var token = getCookieValue("token");
    var sessionId = getCookieValue("sessionId");

    const message = messageInput.value.trim();
    if (!message) return;

    // Display user message
    addMessage(message, 'user');
    messageInput.value = '';

    // Show loading indicator
    const loadingElement = addMessage('Typing...', 'bot', true);

    try {

        $.ajax({
                    url: API_ENDPOINT,
                    crossDomain: true,
                    headers: { "Authorization": token },
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({
                        'message': message,
                        'timestamp': new Date().toISOString(),
                        'sessionId': sessionId
                    }),
                    success: function (data) {
                        document.cookie = `sessionId=${data.sessionId}; path=/; secure; samesite=strict`;
                        
                        loadingElement.remove();
                        
                        // Display bot response
                        addMessage(data.response || 'No response received', 'bot');
                    }
                });

    } catch (error) {
        
        loadingElement.remove();
        
        addMessage('Sorry, there was an error processing your message.', 'bot');
    }
}

// Add message to chat
function addMessage(text, sender, isLoading = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    if (isLoading) {
        messageDiv.classList.add('loading');
    }
    
    messageDiv.textContent = text;
    chatMessages.appendChild(messageDiv);
    
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageDiv;
}

function getToken(auth, success) {
    $.ajax({
        url: COGNITO_DOMAIN + '/oauth2/token',
        type: 'POST',
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        data: { "grant_type": "authorization_code", "client_id": COGNITO_APP_CLIENT_ID, "code": auth, "redirect_uri": REDIRECT_URI },
        success: function (data) {
            success(data);
        }
    });
}

// Function to get a cookie value
function getCookieValue(cookieName) {
    const name = cookieName + '=';
    const cookies = document.cookie.split(';');
    
    for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.indexOf(name) === 0) {
            return cookie.substring(name.length);
        }
    }
    return null;
}

// Function to check if token is expired
function isTokenExpired(token) {
    if (!token) return true;
    
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload.exp * 1000 < Date.now();
    } catch (e) {
        return true;
    }
}

function getParameterByName(name, url) {
    if (!url) url = window.location.href;
    name = name.replace(/[\[\]]/g, "\\$&");
    var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
        results = regex.exec(url);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, " "));
}


$().ready(function () {
    var token = getCookieValue("token");

    if (token == '' || isTokenExpired(token)) {
        var auth = getParameterByName('code');
        var loginUrl = COGNITO_DOMAIN + '/login?redirect_uri=' + REDIRECT_URI + '&response_type=code&client_id=' + COGNITO_APP_CLIENT_ID;
        if (auth === null) {
            window.location.replace(loginUrl);
        }
        else {
            getToken(auth,
                function (data) {
                    var token = data.id_token;
                    var accessToken = data.access_token;
                    
                    document.cookie = `token=${token}; path=/; secure; samesite=strict`;
                    document.cookie = `accessToken=${accessToken}; path=/; secure; samesite=strict`;
                });
        }
    }
});

// Initialize with welcome message
addMessage('Hello! I\'m ready to chat. Send me a message!', 'bot');