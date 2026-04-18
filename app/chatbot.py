# app/chatbot.py
import random
import re
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class ChatbotEngine:
    """Advanced rule-based chatbot with context awareness"""
    
    def __init__(self):
        self.conversation_context: Dict[int, Dict] = {}
        self.responses = {
            # Greetings
            r'^(hello|hi|hey|greetings|sup|yo)$': [
                "Hello! 👋 How can I help you today?",
                "Hi there! Welcome to our platform! 🚀",
                "Hey! Great to see you! What brings you here today?"
            ],
            
            # How are you
            r'how are you|how do you do|how\'s it going': [
                "I'm doing fantastic! Ready to assist you with anything you need! 😊",
                "I'm functioning perfectly! How can I make your day better?",
                "All systems operational! What can I help you with?"
            ],
            
            # Name inquiry
            r'what is your name|who are you|your name': [
                "I'm your AI Assistant! I'm here to help you navigate and use this platform. 🤖",
                "I'm the Hackathon Assistant Bot! Think of me as your digital companion.",
                "I'm your friendly AI assistant, created to make your experience awesome!"
            ],
            
            # Help
            r'help|what can you do|capabilities': [
                "I can help you with:\n📝 Answering questions\n💡 Providing information\n💬 Having natural conversations\n🔍 Finding resources\n🎯 And much more! Just ask me anything!",
                "My superpowers include: conversation, information sharing, and being your personal assistant! What would you like to know?",
                "I'm here to chat, answer questions, and help you make the most of this platform. Try asking me about the project features!"
            ],
            
            # Thanks
            r'thank|thanks|appreciate|good bot': [
                "You're very welcome! Happy to help! 🎉",
                "My pleasure! Don't hesitate to ask if you need anything else!",
                "Thanks! I'm here 24/7 to assist you!"
            ],
            
            # Goodbye
            r'bye|goodbye|see you|farewell': [
                "Goodbye! Have a wonderful day! Come back anytime! 👋",
                "See you later! It was great chatting with you!",
                "Farewell! Remember, I'm always here when you need me!"
            ],
            
            # Project features
            r'authentication|login|signup|register': [
                "Our authentication system is secure and feature-rich! It includes email verification, password reset, JWT tokens, and session management.",
                "You can sign up, log in, reset passwords, and manage your account securely. All passwords are encrypted using bcrypt!"
            ],
            
            # Chatbot about itself
            r'how do you work|are you ai|intelligent': [
                "I'm a smart chatbot that learns from conversations! I can understand natural language and provide helpful responses.",
                "I use advanced pattern matching and context awareness to give you the best responses. Pretty cool, right?"
            ],
            
            # Compliments
            r'you are (awesome|cool|great|amazing|smart)': [
                "Thank you! You're pretty awesome yourself! 😊",
                "I appreciate that! I try my best to be helpful!",
                "Thanks for the kind words! You just made my day!"
            ],
            
            # Default responses
            'default': [
                "That's interesting! Tell me more about that.",
                "I see. Could you elaborate a bit more?",
                "Interesting perspective! What else would you like to share?",
                "I understand. How can I assist you further with that?",
                "Great point! Is there anything specific you'd like to know?"
            ]
        }
    
    def get_response(self, message: str, session_id: Optional[int] = None) -> str:
        """Generate intelligent response based on message content"""
        message_lower = message.lower().strip()
        
        # Update context
        if session_id:
            if session_id not in self.conversation_context:
                self.conversation_context[session_id] = {"last_topic": None, "count": 0}
            self.conversation_context[session_id]["count"] += 1
        
        # Check for matching patterns (priority from most specific to general)
        for pattern, responses in self.responses.items():
            if pattern != 'default':
                try:
                    if re.search(pattern, message_lower, re.IGNORECASE):
                        response = random.choice(responses)
                        if session_id:
                            self.conversation_context[session_id]["last_topic"] = pattern
                        return response
                except re.error:
                    continue
        
        # Handle longer conversations with varied responses
        if session_id and self.conversation_context[session_id]["count"] > 3:
            varied_responses = [
                "I'm really enjoying our conversation! What's on your mind?",
                "You're full of interesting questions! Keep them coming!",
                "This is a great discussion! What would you like to explore next?"
            ]
            return random.choice(varied_responses)
        
        # Return default response
        return random.choice(self.responses['default'])

# Create a global instance
chatbot_engine = ChatbotEngine()