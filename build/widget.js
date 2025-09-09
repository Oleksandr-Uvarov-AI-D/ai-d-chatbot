(function() {
    // Prevent multiple initializations
    if (window.AI_DChatWidgetInitialized) return;
    window.AI_DChatWidgetInitialized = true;
    
    const config = {
        branding: {
            // logo: '../build/logo.png',
            logo: "logo.png",
            name: 'AI-D',
            welcomeText: 'Hallo, hoe kunnen we je helpen?',
            responseTimeText: 'Onze AI-assistent Jaimes staat voor je klaar',
            poweredBy: {
                text: 'Powered by ai-d',
                link: 'https://ai-d.be'
            }
        },
        style: {
            primaryColor: '',
            secondaryColor: '',
            position: 'right',
            backgroundColor: '#ffffff',
            fontColor: '#333333'
        }
    };

    const widgetContainer = document.createElement('div');
    widgetContainer.className = 'ai-d-chat-widget';
    
    const toggleButton = document.createElement('button');
    toggleButton.className = `chat-toggle${config.style.position === 'left' ? ' position-left' : ''}`;
    toggleButton.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <path d="M12 2C6.477 2 2 6.477 2 12c0 1.821.487 3.53 1.338 5L2.5 21.5l4.5-.838A9.955 9.955 0 0012 22c5.523 0 10-4.477 10-10S17.523 2 12 2zm0 18c-1.476 0-2.886-.313-4.156-.878l-3.156.586.586-3.156A7.962 7.962 0 014 12c0-4.411 3.589-8 8-8s8 3.589 8 8-3.589 8-8 8z"/>
        </svg>`;
    
    const chatContainer = document.createElement('div');
    chatContainer.className = `chat-container${config.style.position === 'left' ? ' position-left' : ''}`;

        const newConversationHTML = `
        <div class="brand-header">
            <img src="${config.branding.logo}" alt="${config.branding.name}">
            <span>${config.branding.name}</span>
            <button class="close-button">×</button>
        </div>
        <div class="new-conversation">
            <h2 class="welcome-text">${config.branding.welcomeText}</h2>
            <button class="new-chat-btn">
                <svg class="message-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                    <path fill="currentColor" d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.2L4 17.2V4h16v12z"/>
                </svg>
                Stuur ons een bericht.
            </button>
            <p class="response-text">${config.branding.responseTimeText}</p>
        </div>
    `;

    const chatInterfaceHTML = `
        <div class="chat-interface">
            <div class="brand-header">
                <img src="${config.branding.logo}" alt="${config.branding.name}">
                <span>${config.branding.name}</span>
                <button class="close-button">×</button>
            </div>
            <div class="chat-messages"></div>
            <div class="chat-input">
                <textarea placeholder="Type your message here..." rows="1"></textarea>
                <button type="submit">Send</button>
            </div>
            <div class="chat-footer">
                <a href="${config.branding.poweredBy.link}" target="_blank">${config.branding.poweredBy.text}</a>
            </div>
        </div>
    `;

    chatContainer.innerHTML = newConversationHTML + chatInterfaceHTML;


    widgetContainer.appendChild(toggleButton);  
    widgetContainer.appendChild(chatContainer);

    document.body.appendChild(widgetContainer);

    const newChatBtn = chatContainer.querySelector('.new-chat-btn');
    const chatInterface = chatContainer.querySelector('.chat-interface');
    const messagesContainer = chatContainer.querySelector('.chat-messages');
    const textarea = chatContainer.querySelector('textarea');
    const sendButton = chatContainer.querySelector('button[type="submit"]');


    // Used to check whether a conversation ran for too much time without a user's input.
    let userIsLate = false;

    // Used to end a conversation after receiving a final message
    let conversationEnded = false;

    // Used to reset the timeout if the user sends a message before the time has run out
    let timeoutId;

    let userConversationMessage;

    async function endConversation() {
        // const response = await fetch("http://127.0.0.1:8000/end_conversation", {
        const response = await fetch("https://ai-d-chatbot-bzot.onrender.com/end_conversation", {
            method: "POST",
            headers: {"Content-type": "application/json"},
            body: JSON.stringify({thread_id: sessionStorage.getItem("thread_id")})
        });
    }

    // Time user has to reply 
    function startTimeout() {
        if (timeoutId) {
            clearTimeout(timeoutId);
        }

        timeoutId = setTimeout(async () => {
        const botMessageDiv = document.createElement('div');
        botMessageDiv.className = 'chat-message bot';
        botMessageDiv.textContent = "Het spijt ons, maar de tijd van het gesprek is voorbij. " +
                                    "U kunt ons nogmaals contacteren als u een vraag hebt.";
        messagesContainer.appendChild(botMessageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        userIsLate = true;

        endConversation();
    }, 600000);
    }

    function appendBotMessage(message) {
        const botMessageDiv = document.createElement('div');
        botMessageDiv.className = 'chat-message bot';
        botMessageDiv.textContent = message;
        messagesContainer.appendChild(botMessageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }


    async function startNewConversation(userMessage) {   
        startTimeout(); 

        let messageToSend = null;
        // message bubble with three dots
        let indicator = null;
        // userMessage is not null in case the user is starting a conversation anew
        // (when the time of the previous one ran out)
        if (userMessage) {
            messageToSend = userMessage;
            const userMessageDiv = document.createElement('div');
            userMessageDiv.className = 'chat-message user';
            userMessageDiv.textContent = userMessage;
            messagesContainer.appendChild(userMessageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            indicator = showTypingIndicator();
        } else {
            chatContainer.querySelector('.brand-header').style.display = 'none';
            chatContainer.querySelector('.new-conversation').style.display = 'none';
            chatInterface.classList.add('active');
            appendBotMessage("Hallo, ik ben Jaimes, de AI-assistent van AI-D. Waarmee kan ik je vandaag helpen?");
        }


        // const response = await fetch("http://127.0.0.1:8000/start", {
        const response = await fetch("https://ai-d-chatbot-bzot.onrender.com/start", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({message: messageToSend})
        });

        const data = await response.json();
        
        sessionStorage.setItem("thread_id", data.thread_id);

        if (userMessage) {
            appendBotMessage(data.message);
            removeTypingIndicator(indicator);
        }
    }

    async function sendMessage(userMessage) {
        startTimeout();
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'chat-message user';
        userMessageDiv.textContent = userMessage;
        messagesContainer.appendChild(userMessageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;


        const indicator = showTypingIndicator();

        // const response = await fetch("http://127.0.0.1:8000/chat", {
        const response = await fetch("https://ai-d-chatbot-bzot.onrender.com/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({message: userMessage, thread_id: sessionStorage.getItem("thread_id")})
        });

        const data = await response.json();

        removeTypingIndicator(indicator);

        if (data.message === "True") {
            appendBotMessage("Ons gesprek is afgerond. Heb je later nog vragen? Dan kan je ons altijd opnieuw contacteren. This conversation ended. If you want to start a new conversation, send a new message.")
            clearTimeout(timeoutId);
            endConversation();
            conversationEnded = true;
        } else {
          appendBotMessage(data.message);    
        }
    }


    newChatBtn.addEventListener('click', () => {
       startNewConversation(null)     
    } );

    function continueConversation() {
        userConversationMessage = textarea.value.trim();
        if (userConversationMessage) {
            if (userIsLate || conversationEnded) {
                startNewConversation(userConversationMessage);
                conversationEnded = false;
            } else {
                sendMessage(userConversationMessage);
            }
            userIsLate = false;
            textarea.value = '';
        } 
    }

    textarea.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            continueConversation();
        }
    });

    sendButton.addEventListener('click', () => {
        continueConversation();
    });

    toggleButton.addEventListener('click', () => {
        chatContainer.classList.toggle('open');
    });


    // Add close button handlers
    const closeButtons = chatContainer.querySelectorAll('.close-button');
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            chatContainer.classList.remove('open');
        });
    });

    function showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'chat-message bot typing-indicator';
        indicator.innerHTML = `
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
        `;
        messagesContainer.appendChild(indicator);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return indicator; // so you can remove it later
        }

    function removeTypingIndicator(indicator) {
        if (indicator && indicator.parentNode) {
            indicator.parentNode.removeChild(indicator);
        }
        }

})();