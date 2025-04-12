import { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

const ChatContext = createContext();

export function ChatProvider({ children }) {
  // Basic chat state
  const [chatSessions, setChatSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // Document-related state
  const [isFilesPanelOpen, setIsFilesPanelOpen] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [hasDocuments, setHasDocuments] = useState(false);
  
  // Toggle states for features
  const [useRAG, setUseRAG] = useState(false);
  const [useWebSearch, setUseWebSearch] = useState(false);
  // Web search types state - defaulting to all three types
  const [searchTypes, setSearchTypes] = useState({
    web: true,
    academic: true,
    social: true
  });

  // Model selection state
  const [availableModels, setAvailableModels] = useState([
    { id: "gpt-4o-mini", name: "GPT-4o (mini)", description: "Fast and efficient for everyday tasks" },
    { id: "gpt-4o", name: "GPT-4o", description: "Most capable model with advanced reasoning" }
  ]);
  const [currentModel, setCurrentModel] = useState(availableModels[0]);

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

  // Automatically check for documents on startup
  useEffect(() => {
    checkForDocuments();
  }, []);

  // Check if documents exist in the vectorstore
  const checkForDocuments = async () => {
    try {
      const response = await axios.get(`${API_URL}/list_vectorstore_docs`);
      if (response.data.status === 'success') {
        // Update hasDocuments state based on backend response
        setHasDocuments(response.data.has_documents);
        
        // If documents exist, set RAG to enabled by default
        if (response.data.has_documents) {
          setUseRAG(true);
        }
        
        // Update documents list
        setDocuments(response.data.documents.map((filename, index) => ({
          id: `vectorstore-${index}`,
          name: filename.replace('docs\\', '').replace('docs/', ''),
          type: 'PDF',
          uploaded_at: new Date().toISOString()
        })));
      }
    } catch (error) {
      console.error('Error checking for documents:', error);
      setHasDocuments(false);
    }
  };

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
        // Update hasDocuments based on backend response
        setHasDocuments(response.data.has_documents);
        
        // Convert to file format for easier display
        const formattedDocs = response.data.documents.map((filename, index) => {
          const name = filename.replace('docs\\', '').replace('docs/', ''); // Remove docs\ or docs/ prefix
          const extension = name.split('.').pop().toUpperCase(); // Get file extension
          return {
            id: `vectorstore-${index}`,
            name: name,
            type: extension || 'PDF', // Use the file extension or default to PDF
            uploaded_at: new Date().toISOString()
          };
        });
        setDocuments(formattedDocs);
      }
    } catch (error) {
      console.error('Error loading documents:', error);
      setHasDocuments(false);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  const sendMessage = async (message) => {
    if (!currentSession || !message.trim()) return;

    try {
      setLoading(true);
      
      // Create user message object
      const userMessage = { type: 'human', content: message };
      
      // Update chat history with user message - use function form to ensure latest state
      setChatHistory(prevHistory => [...prevHistory, userMessage]);
      
      // Get currently active search types as array
      const activeSearchTypes = Object.entries(searchTypes)
        .filter(([_, isActive]) => isActive)
        .map(([type]) => type);
      
      // Make the API call to get the AI response
      const response = await axios.post(`${API_URL}/chat`, {
        session_key: currentSession,
        query: message,
        enable_web_search: useWebSearch,
        enable_rag: useRAG,
        search_types: activeSearchTypes,
        model: currentModel.id
      });

      // Handle the AI response when received
      if (response.data.response) {
        // Create AI message object
        const aiMessage = {
          type: 'ai', 
          content: response.data.response,
          document_info: response.data.document_info,
          web_info: response.data.web_info
        };
        
        // Update chat history with AI response - use function form to ensure latest state
        setChatHistory(prevHistory => [...prevHistory, aiMessage]);
        
        // Update hasDocuments state based on response
        if (response.data.hasOwnProperty('has_documents')) {
          setHasDocuments(response.data.has_documents);
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setLoading(false);
    }
  };

  // Toggle web search type function 
  const toggleSearchType = (type) => {
    setSearchTypes(prev => {
      // Count currently active types
      const activeCount = Object.values(prev).filter(Boolean).length;
      
      // If trying to disable a type when there's only one active, don't allow it
      if (prev[type] && activeCount === 1) {
        return prev; // Return unchanged state
      }
      
      // Toggle the specified type
      return { ...prev, [type]: !prev[type] };
    });
  };

  // Simple web search toggle function
  const toggleWebSearch = () => {
    setUseWebSearch(!useWebSearch);
  };
  
  // Toggle RAG functionality
  const toggleRAG = async () => {
    // Check for documents first to ensure we have the latest status
    try {
      const response = await axios.get(`${API_URL}/list_vectorstore_docs`);
      if (response.data.status === 'success') {
        // Update hasDocuments state based on backend response
        const documentsExist = response.data.has_documents;
        setHasDocuments(documentsExist);
        
        // Only toggle if we have documents
        if (documentsExist) {
          setUseRAG(!useRAG);
        } else {
          // Force RAG to be off if no documents exist
          setUseRAG(false);
        }
      }
    } catch (error) {
      console.error('Error checking for documents:', error);
      // On error, assume no documents to be safe
      setHasDocuments(false);
      setUseRAG(false);
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
    if (files.length === 0) return;
    
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }
    
    try {
      setLoading(true);
      const response = await axios.post(`${API_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      if (response.data.status === 'success') {
        // Reload the documents list to show newly uploaded documents
        await loadDocuments();
        
        // Enable RAG automatically when documents are uploaded
        setUseRAG(true);
        setHasDocuments(true);
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
  };
  
  const toggleFilesPanel = (isOpen = null) => {
    setIsFilesPanelOpen(prev => isOpen !== null ? isOpen : !prev);
    if (isFilesPanelOpen === false && isOpen !== false) {
      loadDocuments();
    }
  };
  
  const deleteDocument = async (filename) => {
    try {
      const encodedFilename = encodeURIComponent(filename);
      const response = await axios.delete(`${API_URL}/delete_document?filename=${encodedFilename}`);
      if (response.data.status === 'success') {
        // Update documents and hasDocuments state based on backend response
        setDocuments(response.data.documents.map((filename, index) => {
          const name = filename.replace('docs\\', '').replace('docs/', '');
          const extension = name.split('.').pop().toUpperCase();
          return {
            id: `vectorstore-${index}`,
            name: name,
            type: extension || 'PDF',
            uploaded_at: new Date().toISOString()
          };
        }));
        
        // Update hasDocuments state
        const hasRemainingDocs = response.data.has_documents;
        setHasDocuments(hasRemainingDocs);
        
        // If no documents remain, force RAG off
        if (!hasRemainingDocs) {
          setUseRAG(false);
        }
        
        return true;
      }
      return false;
    } catch (error) {
      console.error('Error deleting document:', error);
      // On error, check for document status to keep frontend in sync
      checkForDocuments();
      return false;
    }
  };

  // Function to change the current model
  const changeModel = (modelId) => {
    const selectedModel = availableModels.find(model => model.id === modelId);
    if (selectedModel) {
      setCurrentModel(selectedModel);
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
        useWebSearch,
        isFilesPanelOpen,
        documents,
        isLoadingDocs,
        hasDocuments,
        searchTypes,
        createNewChat,
        loadChatHistory,
        sendMessage,
        clearChat,
        deleteChat,
        switchChat,
        toggleRAG,
        toggleWebSearch,
        toggleFilesPanel,
        uploadDocuments,
        loadDocuments,
        deleteDocument,
        loadChatSessions,
        toggleSearchType,
        availableModels,
        currentModel,
        changeModel
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export const useChat = () => useContext(ChatContext);