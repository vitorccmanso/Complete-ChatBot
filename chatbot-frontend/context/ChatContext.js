import { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

const ChatContext = createContext();

export function ChatProvider({ children }) {
  const [chatSessions, setChatSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [useRAG, setUseRAG] = useState(true);
  const [isFilesPanelOpen, setIsFilesPanelOpen] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);

  // Load chat sessions initially
  useEffect(() => {
    loadChatSessions();
  }, []);

  // Load chat history when session changes
  useEffect(() => {
    if (currentSession) {
      loadChatHistory(currentSession);
    }
  }, [currentSession]);

  const loadChatSessions = async () => {
    try {
      const response = await axios.get(`${API_URL}/list_chats`);
      if (response.data.status === 'success') {
        setChatSessions(response.data.chat_sessions);
        if (response.data.chat_sessions.length > 0 && !currentSession) {
          const mostRecent = response.data.chat_sessions[0];
          const sessionKey = mostRecent.split('.')[0];
          setCurrentSession(sessionKey);
          loadChatHistory(sessionKey);
        }
      }
    } catch (error) {
      console.error('Error loading chat sessions:', error);
    }
  };

  const createNewChat = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`${API_URL}/create_chat`);
      if (response.data.status === 'success') {
        const newSessionKey = response.data.session_key;
        setCurrentSession(newSessionKey);
        setChatHistory([]);
        
        // Instead of calling loadChatSessions, manually update the sessions list
        // to put the new chat at the top
        const newChatFilename = `${newSessionKey}.json`;
        setChatSessions(prevSessions => [newChatFilename, ...prevSessions]);
      }
    } catch (error) {
      console.error('Error creating new chat:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadChatHistory = async (sessionKey) => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/chat_history?session_key=${sessionKey}`);
      if (response.data.status === 'success') {
        setChatHistory(response.data.history);
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
    } finally {
      setLoading(false);
    }
  };

  // Function to load documents from vectorstore
  const loadDocuments = async () => {
    // Don't start a new load if one is already in progress
    if (isLoadingDocs) return;
    
    try {
      setIsLoadingDocs(true);
      const response = await axios.get(`${API_URL}/list_vectorstore_docs`);
      if (response.data.status === 'success') {
        // Convert to file format for easier display
        const formattedDocs = response.data.documents.map((filename, index) => ({
          id: `vectorstore-${index}`,
          name: filename.replace('docs\\', '').replace('docs/', ''), // Remove docs\ or docs/ prefix
          type: 'PDF',
          uploaded_at: new Date().toISOString()
        }));
        setDocuments(formattedDocs);
      }
    } catch (error) {
      console.error('Error loading documents:', error);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  const sendMessage = async (message) => {
    if (!currentSession || !message.trim()) return;

    try {
      setLoading(true);
      const updatedHistory = [...chatHistory, { type: 'human', content: message }];
      setChatHistory(updatedHistory);

      const response = await axios.post(`${API_URL}/chat`, {
        session_key: currentSession,
        query: message,
        use_rag: useRAG
      });

      if (response.data.response) {
        setChatHistory([
          ...updatedHistory, 
          { 
            type: 'ai', 
            content: response.data.response,
            document_info: response.data.document_info 
          }
        ]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = async () => {
    if (!currentSession) return;

    try {
      const response = await axios.post(`${API_URL}/clear_chat?session_key=${currentSession}`);
      if (response.data.status === 'success') {
        setChatHistory([]);
      }
    } catch (error) {
      console.error('Error clearing chat:', error);
    }
  };

  const deleteChat = async (sessionKey) => {
    try {
      const response = await axios.post(`${API_URL}/delete_chat?session_key=${sessionKey}`);
      if (response.data.status === 'success') {
        // Instead of reloading from server, update local state
        setChatSessions(prevSessions => {
          return prevSessions.filter(session => !session.startsWith(`${sessionKey}.`));
        });
        
        // If we deleted the current session, clear it
        if (currentSession === sessionKey) {
          setCurrentSession(null);
          setChatHistory([]);
          
          // If there are other chats, select the first one
          setTimeout(() => {
            if (chatSessions.length > 1) {
              const nextSession = chatSessions.find(s => !s.startsWith(`${sessionKey}.`));
              if (nextSession) {
                const nextSessionKey = nextSession.split('.')[0];
                switchChat(nextSessionKey);
              }
            }
          }, 0);
        }
      }
    } catch (error) {
      console.error('Error deleting chat:', error);
    }
  };

  const uploadDocuments = async (files) => {
    if (!files || files.length === 0 || !currentSession) return;

    const formData = new FormData();
    for (const file of files) {
      formData.append('pdfs', file);
    }
    
    // Add the session key to the form data
    formData.append('session_key', currentSession);

    try {
      setLoading(true);
      const response = await axios.post(`${API_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      // If upload was successful, update our list of files
      if (response.data.status === 'success') {
        // Also refresh the documents list and open the files panel
        await loadDocuments();
        setIsFilesPanelOpen(true);
      }
      
      return response.data;
    } catch (error) {
      console.error('Error uploading documents:', error);
      return { status: 'error', message: error.message };
    } finally {
      setLoading(false);
    }
  };

  const switchChat = (sessionKey) => {
    setCurrentSession(sessionKey);
    loadChatHistory(sessionKey);
  };

  const toggleRAG = () => {
    setUseRAG(!useRAG);
  };
  
  // Toggle the files panel open/closed
  const toggleFilesPanel = (isOpen = null) => {
    setIsFilesPanelOpen(isOpen !== null ? isOpen : !isFilesPanelOpen);
  };

  // Delete a document from the vectorstore and file system
  const deleteDocument = async (filename) => {
    try {
      // Call the backend endpoint to delete the document
      const response = await axios.delete(`${API_URL}/delete_document?filename=${filename}`);
      
      if (response.data.status === 'success') {
        // Update the documents list by removing the deleted document
        setDocuments(prevDocs => prevDocs.filter(doc => doc.name !== filename));
        return true;
      } else {
        console.error('Error deleting document:', response.data.message);
        return false;
      }
    } catch (error) {
      console.error('Error deleting document:', error);
      return false;
    }
  };

  return (
    <ChatContext.Provider
      value={{
        chatSessions,
        currentSession,
        chatHistory,
        loading,
        useRAG,
        isFilesPanelOpen,
        documents,
        loadChatSessions,
        createNewChat,
        sendMessage,
        clearChat,
        deleteChat,
        uploadDocuments,
        switchChat,
        toggleRAG,
        toggleFilesPanel,
        loadDocuments,
        deleteDocument
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export const useChat = () => useContext(ChatContext);