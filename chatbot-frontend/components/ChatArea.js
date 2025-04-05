// Import React hooks for state, refs, effects, and memoization
import React, { useState, useRef, useEffect, useCallback, memo } from 'react';
// Import UI components from Chakra UI
import {
  Box,
  Flex,
  Input,
  Button,
  VStack,
  Text,
  IconButton,
  Spinner,
  FormControl,
  Switch,
  FormLabel,
  HStack,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Container,
  useToast,
  Progress,
  Badge,
  Divider,
  Tooltip,
  Heading,
  Collapse,
} from '@chakra-ui/react';
// Import icons from react-icons library
import { FiSend, FiTrash2, FiUpload, FiCopy, FiFile, FiX, FiFileText, FiDownload, FiChevronLeft, FiChevronDown, FiChevronUp, FiArrowDown } from 'react-icons/fi';
// Import our custom hook to access chat functionality
import { useChat } from '../context/ChatContext';
// Import ReactMarkdown for rendering markdown responses
import ReactMarkdown from 'react-markdown';
// Import syntax highlighter for code blocks
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
// Changed import to use a style that is definitely available
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';
// Import KaTeX for LaTeX math rendering - using dynamic imports instead of CSS import
import { InlineMath, BlockMath } from 'react-katex';

// Custom components for ReactMarkdown to render Markdown with Chakra UI styling
const MarkdownComponents = {
  // Basic text elements
  p: (props) => <Text mb={3} lineHeight="1.6" {...props} />, // Paragraphs
  h1: (props) => <Text fontSize="2xl" fontWeight="bold" my={4} {...props} />, // Heading 1
  h2: (props) => <Text fontSize="xl" fontWeight="bold" my={3} {...props} />, // Heading 2
  h3: (props) => <Text fontSize="lg" fontWeight="bold" my={2} {...props} />, // Heading 3
  // List elements
  ul: (props) => <Box as="ul" pl={4} mb={2} {...props} />, // Unordered list
  ol: (props) => <Box as="ol" pl={4} mb={2} {...props} />, // Ordered list
  li: (props) => <Box as="li" ml={4} mb={1} {...props} />, // List item
  // Code block with syntax highlighting and copy button
  code: memo((props) => {
    const { className, children } = props;
    // Extract language from className, if available
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : '';
    const toast = useToast(); // Toast for showing copy success/failure
    
    // Function to copy code to clipboard
    const handleCopyCode = () => {
      navigator.clipboard.writeText(children).then(
        () => {
          // Show success toast when copy succeeds
          toast({
            title: "Code copied",
            status: "success",
            duration: 2000,
            isClosable: true,
            position: "top",
          });
        },
        (err) => {
          // Show error toast when copy fails
          toast({
            title: "Failed to copy",
            description: err.message,
            status: "error",
            duration: 2000,
            isClosable: true,
            position: "top",
          });
        }
      );
    };
    
    // If it's a code block with language (like ```javascript)
    if (match) {
      return (
        <Box 
          my={3} 
          borderRadius="md" 
          overflow="hidden" 
          border="1px solid rgba(255, 255, 255, 0.1)"
          boxShadow="0 1px 2px rgba(0, 0, 0, 0.2)"
        >
          {/* Header showing language and copy button */}
          <Flex 
            bg="#2d2d2d" 
            px={3} 
            py={1} 
            color="#abb2bf" 
            alignItems="center"
            justifyContent="space-between"
            borderBottom="1px solid rgba(255, 255, 255, 0.1)"
          >
            <Text fontSize="0.8rem" fontFamily="monospace">{language}</Text>
            <IconButton
              icon={<FiCopy />}
              aria-label="Copy code"
              size="xs"
              variant="ghost"
              color="#abb2bf"
              onClick={handleCopyCode}
              _hover={{ bg: "rgba(255, 255, 255, 0.1)" }}
            />
          </Flex>
          {/* Code content with syntax highlighting */}
          <SyntaxHighlighter
            language={language}
            style={oneDark}
            customStyle={{
              margin: 0,
              padding: '1rem',
              borderRadius: '0',
              fontSize: '0.9em',
            }}
            showLineNumbers={false}
            wrapLines={false}
            useInlineStyles={true}
          >
            {children}
          </SyntaxHighlighter>
        </Box>
      );
    } else {
      // If it's inline code (like `code`)
      return (
        <Text
          as="span"
          px={1}
          bg="rgba(171, 178, 191, 0.15)"
          color="#e06c75"
          borderRadius="sm"
          fontFamily="monospace"
          fontSize="0.9em"
          border="1px solid rgba(171, 178, 191, 0.2)"
        >
          {children}
        </Text>
      );
    }
  }),
  // Other markdown elements
  pre: (props) => <Box as="pre" w="100%" {...props} />, // Preformatted text
  blockquote: (props) => (
    <Box
      as="blockquote"
      borderLeftWidth="4px"
      borderLeftColor="gray.300"
      pl={4}
      py={2}
      my={4}
      {...props}
    />
  ),
};

// Memoize the component to prevent unnecessary re-renders
const MemoizedMarkdown = memo(({ content }) => {
  // Function to safely render LaTeX math
  const renderMath = (latex, isBlock = false) => {
    try {
      if (isBlock) {
        return <BlockMath math={latex} />;
      } else {
        return <InlineMath math={latex} />;
      }
    } catch (err) {
      console.error("Error rendering LaTeX:", err, "LaTeX content:", latex);
      return <Text as="span" color="red.400">{isBlock ? `$$${latex}$$` : `$${latex}$`}</Text>;
    }
  };
  
  // Direct approach to render both markdown and LaTeX
  const renderContent = () => {
    // Handle block math expressions first - split the content by block math delimiters
    const blockParts = content.split(/(\$\$[\s\S]+?\$\$)/g);
    
    return blockParts.map((part, blockIndex) => {
      // Check if this part is a block math expression
      if (part.startsWith('$$') && part.endsWith('$$') && part.length > 4) {
        // Extract the LaTeX (removing the $$ delimiters)
        const latex = part.slice(2, -2).trim();
        return (
          <Box key={`block-${blockIndex}`} my={4} mx="auto" textAlign="center" width="100%">
            {renderMath(latex, true)}
          </Box>
        );
      } else {
        // For non-block math parts, we need to process inline math
        
        // Enhanced inline math detection - handles more edge cases
        // Create a custom renderer for all text components to properly handle inline math
        const customComponents = {
          ...MarkdownComponents,
          // Custom paragraph renderer
          p: ({ children, ...props }) => {
            const processedChildren = React.Children.map(children, child => {
              // Only process string children
              if (typeof child !== 'string') return child;
              
              // Split by inline math delimiters, preserving the delimiters
              const parts = child.split(/(\$[^\$\n]+?\$)/g);
              if (parts.length === 1) return child;
              
              // Process each part
              return parts.map((part, i) => {
                // Check if this part is inline math (starts and ends with $ and has content)
                if (part.startsWith('$') && part.endsWith('$') && part.length > 2) {
                  const latex = part.slice(1, -1).trim();
                  return (
                    <Text 
                      key={`inline-math-${i}`} 
                      as="span" 
                      display="inline" 
                      className="katex-inline"
                    >
                      {renderMath(latex, false)}
                    </Text>
                  );
                }
                // Return regular text as is
                return part.length > 0 ? part : null;
              });
            });
            
            return <Text mb={3} lineHeight="1.6" {...props}>{processedChildren}</Text>;
          },
          // Enhanced strong element handling
          strong: ({ children, ...props }) => {
            // If children is a string and contains math, process it
            if (typeof children === 'string' && children.includes('$')) {
              const parts = [];
              let lastIndex = 0;
              
              // Regular expression to find all inline math expressions
              const inlineMathRegex = /(\$[^\$\n]+?\$)/g;
              let match;
              
              while ((match = inlineMathRegex.exec(children)) !== null) {
                // Add text before the math if any
                if (match.index > lastIndex) {
                  parts.push(
                    <Text 
                      key={`strong-text-${lastIndex}`} 
                      as="span" 
                      fontWeight="bold"
                    >
                      {children.substring(lastIndex, match.index)}
                    </Text>
                  );
                }
                
                // Extract and add the math
                const mathContent = match[0];
                if (mathContent.length > 2) { // Ensure there's actual content
                  const latex = mathContent.slice(1, -1).trim();
                  parts.push(
                    <Text 
                      key={`strong-math-${match.index}`} 
                      as="span" 
                      fontWeight="bold"
                      display="inline" 
                      className="katex-inline"
                    >
                      {renderMath(latex, false)}
                    </Text>
                  );
                }
                
                lastIndex = match.index + match[0].length;
              }
              
              // Add any remaining text
              if (lastIndex < children.length) {
                parts.push(
                  <Text 
                    key={`strong-text-end`} 
                    as="span" 
                    fontWeight="bold"
                  >
                    {children.substring(lastIndex)}
                  </Text>
                );
              }
              
              return <>{parts}</>;
            }
            
            // Return normal strong rendering for non-math content
            return <Text as="span" fontWeight="bold" {...props}>{children}</Text>;
          },
          // Similar handling for other text-based elements
          li: props => {
            const { children, ...rest } = props;
            // Process only if children is a string and contains math delimiters
            if (typeof children === 'string' && children.includes('$')) {
              const parts = children.split(/(\$[^\$\n]+?\$)/g);
              const processedParts = parts.map((part, i) => {
                if (part.startsWith('$') && part.endsWith('$') && part.length > 2) {
                  const latex = part.slice(1, -1).trim();
                  return (
                    <Text key={`li-math-${i}`} as="span" display="inline" className="katex-inline">
                      {renderMath(latex, false)}
                    </Text>
                  );
                }
                return part;
              });
              return <Box as="li" ml={4} mb={1} {...rest}>{processedParts}</Box>;
            }
            return <Box as="li" ml={4} mb={1} {...props} />;
          }
        };
        
        // Render the part with our enhanced components
        return (
          <ReactMarkdown 
            key={`text-${blockIndex}`} 
            components={customComponents}
          >
            {part}
          </ReactMarkdown>
        );
      }
    });
  };

  return <>{renderContent()}</>;
});

// Sources component to display document information
const Sources = ({ documentInfo }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!documentInfo || documentInfo.length === 0) {
    return null;
  }

  const handleClick = () => {
    setIsOpen(!isOpen);
  };

  // Split the document info into lines and parse each line
  const sources = documentInfo.split('\n').filter(line => line.trim().length > 0);

  return (
    <Box mt={2}>
      <Button 
        size="xs" 
        variant="outline" 
        onClick={handleClick}
        rightIcon={isOpen ? <FiChevronUp /> : <FiChevronDown />}
        color="gray.500"
        fontWeight="normal"
        fontSize="sm"
        py={1}
        height="auto"
        borderColor="gray.600"
        _hover={{ bg: "rgba(255, 255, 255, 0.05)" }}
      >
        Sources
      </Button>
      
      <Collapse in={isOpen} animateOpacity>
        <Box 
          mt={2} 
          p={3} 
          borderRadius="md" 
          bg="var(--input-bg)"
          border="1px solid var(--border-color)"
        >
          <VStack align="stretch" spacing={2}>
            {sources.map((source, index) => (
              <Box key={index} p={2} borderRadius="md" _hover={{ bg: "rgba(255, 255, 255, 0.05)" }}>
                <Text fontSize="sm" color="gray.500">
                  {source}
                </Text>
              </Box>
            ))}
          </VStack>
        </Box>
      </Collapse>
    </Box>
  );
};

// Component for the Files Panel (right sidebar)
const FilesPanel = ({ files, onClose, onDeleteDocument }) => {
  return (
    <Box
      w="300px"
      h="100vh"
      bg="var(--sidebar-bg)"
      borderLeft="1px"
      borderColor="var(--border-color)"
      position="fixed"
      top={0}
      right={0}
      zIndex={10}
      overflowY="auto"
      transition="all 0.3s ease-in-out"
      css={{
        '&::-webkit-scrollbar': {
          width: '8px',
        },
        '&::-webkit-scrollbar-track': {
          background: 'var(--sidebar-bg)',
        },
        '&::-webkit-scrollbar-thumb': {
          background: '#555',
          borderRadius: '4px',
        },
        '&::-webkit-scrollbar-thumb:hover': {
          background: '#777',
        },
      }}
    >
      <Flex justify="space-between" align="center" p={4} borderBottom="1px" borderColor="var(--border-color)">
        <Heading size="md" color="var(--foreground)">Documents</Heading>
        <IconButton
          icon={<FiX />}
          aria-label="Close files panel"
          onClick={onClose}
          variant="ghost"
          color="var(--foreground)"
          _hover={{ bg: "var(--input-bg)" }}
        />
      </Flex>
      
      <VStack spacing={3} align="stretch" p={4} maxH="calc(100vh - 80px)" overflowY="auto">
        {files.length > 0 ? (
          files.map((file, index) => (
            <Box 
              key={index}
              p={3}
              borderRadius="md"
              border="1px solid var(--border-color)"
              bg="var(--input-bg)"
              _hover={{ bg: "rgba(255, 255, 255, 0.05)" }}
              position="relative"
            >
              {/* Delete button in top right */}
              <IconButton
                icon={<FiX size={14} />}
                aria-label="Delete document"
                position="absolute"
                top="5px"
                right="5px"
                size="xs"
                variant="ghost"
                color="gray.500"
                _hover={{ 
                  bg: "rgba(255, 0, 0, 0.1)", 
                  color: "red.300" 
                }}
                onClick={() => onDeleteDocument(file.name)}
                zIndex={2}
              />
              
              <Flex align="center" mb={2}>
                <Box as={FiFileText} mr={2} color="var(--accent-color)" flexShrink={0} />
                <Text 
                  fontSize="sm" 
                  fontWeight="bold" 
                  color="var(--foreground)"
                  wordBreak="break-word"
                  maxW="85%" /* Make room for the delete button */
                >
                  {file.name}
                </Text>
              </Flex>
              <Flex justify="space-between" align="center">
                <Badge colorScheme="blue" size="sm">{file.type || 'PDF'}</Badge>
                <Text fontSize="xs" color="gray.500">
                  {new Date(file.uploaded_at || Date.now()).toLocaleDateString()}
                </Text>
              </Flex>
            </Box>
          ))
        ) : (
          <Box textAlign="center" p={4} color="gray.500">
            <Box as={FiFile} size="2em" mx="auto" mb={2} />
            <Text>No documents uploaded yet</Text>
            <Text fontSize="sm" mt={2}>Upload PDFs using the + button in the chat input</Text>
          </Box>
        )}
      </VStack>
    </Box>
  );
};

// Main ChatArea component that displays messages and input
export default function ChatArea() {
  // Get chat-related functions and state from our context
  const { 
    currentSession,       // Current active chat session
    chatHistory,          // Messages in the current chat
    sendMessage,          // Function to send a message
    clearChat,            // Function to clear the current chat
    loading,              // Loading state for async operations
    useRAG,               // State of RAG feature (on/off)
    toggleRAG,            // Function to toggle RAG
    uploadDocuments,      // Function to upload PDF documents
    isFilesPanelOpen,     // Whether files panel is open
    toggleFilesPanel,     // Function to toggle files panel
    documents,            // List of documents in vectorstore
    loadDocuments,        // Function to refresh documents
    deleteDocument        // Function to delete documents
  } = useChat();
  
  // Local state and refs
  const [message, setMessage] = useState(''); // Current message being typed
  const messagesEndRef = useRef(null);        // Ref for auto-scrolling to bottom
  const messagesContainerRef = useRef(null);  // Ref for the messages container to detect scroll
  const emptyStateInputRef = useRef(null);    // Ref for input in empty state
  const chatInputRef = useRef(null);          // Ref for input in non-empty state
  const fileInputRef = useRef(null);          // Ref for hidden file input
  const [isUploading, setIsUploading] = useState(false); // Track file upload state
  const [selectedFiles, setSelectedFiles] = useState([]); // Files being uploaded currently
  const hasLoadedDocs = useRef(false);        // Track if we've loaded docs for this panel open
  const [showScrollButton, setShowScrollButton] = useState(false); // State to control scroll button visibility
  const toast = useToast();                  // Toast for notifications

  // Calculate height for approximately 12 lines of text
  // Line height is typically around 1.5em, and font size is inherited
  // 12 lines × 1.5 × 16px (typical font size) + padding = ~288px + padding
  const MAX_LINES_HEIGHT = 290; // Slightly higher than 12 lines to account for padding

  // Handle file selection when files are chosen from file explorer
  const handleFileChange = useCallback((e) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      setSelectedFiles(files);
      setIsUploading(true); // Start the upload UI state
      
      // Automatically start upload when files are selected
      uploadDocuments(files)
        .then(result => {
          if (result.status === 'success') {
            // Files are now tracked in the context
            // Just clear the local selection and uploading state
            toggleFilesPanel(true); // Show files panel
          }
          setSelectedFiles([]);
          setIsUploading(false);
          
          // Reset the file input value so the same file can be selected again
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
        })
        .catch(err => {
          console.error("Error uploading files:", err);
          setIsUploading(false);
          setSelectedFiles([]);
          
          // Reset the file input value even on error
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
        });
    }
  }, [uploadDocuments, toggleFilesPanel]);

  // Function to open the file picker dialog
  const handleUploadClick = useCallback(() => {
    // Reset the file input first to ensure the change event will fire
    // even if the user selects the same file again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    // Trigger the hidden file input click to open file explorer
    fileInputRef.current?.click();
  }, []);

  // Handle keyboard events for the message input
  const handleKeyDown = useCallback((e) => {
    // If Enter key is pressed without Shift key, send the message
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault(); // Prevent default behavior (new line)
      
      // Only send if there's a message and we're not loading
      if (message.trim() && currentSession && !loading) {
        sendMessage(message);
        setMessage('');
        
        // Reset textarea height after sending
        if (e.target) {
          e.target.style.height = '60px';
        }
      }
    }
    // If Enter key is pressed with Shift, allow default behavior (new line)
    // No specific handling needed as the default behavior will occur
  }, [message, currentSession, sendMessage, loading]);

  // Handle changes to the message input, including auto-resizing
  const handleMessageInput = useCallback((e) => {
    setMessage(e.target.value);
    
    // Auto-resize the textarea to show all content
    e.target.style.height = '60px'; // Reset height to calculate properly
    e.target.style.height = `${Math.min(MAX_LINES_HEIGHT, e.target.scrollHeight)}px`; // Limit max height to match CSS
  }, []);

  const handleSendMessage = useCallback((e) => {
    e.preventDefault();
    if (message.trim() && currentSession) {
      sendMessage(message);
      setMessage('');
    }
  }, [message, currentSession, sendMessage]);

  // Ensure textareas are properly sized when message content changes
  useEffect(() => {
    const resizeTextarea = (element) => {
      if (element) {
        element.style.height = '60px';
        element.style.height = `${Math.min(MAX_LINES_HEIGHT, element.scrollHeight)}px`;
      }
    };

    resizeTextarea(emptyStateInputRef.current);
    resizeTextarea(chatInputRef.current);
  }, [message]);

  // Focus input when chat is opened
  useEffect(() => {
    if (currentSession) {
      if (chatHistory.length === 0 && emptyStateInputRef.current) {
        setTimeout(() => {
          emptyStateInputRef.current?.focus();
        }, 100);
      } else if (chatHistory.length > 0 && chatInputRef.current) {
        setTimeout(() => {
          chatInputRef.current?.focus();
        }, 100);
      }
    }
  }, [currentSession, chatHistory.length]);

  // Handle scroll in messages area to show/hide scroll button
  const handleScroll = useCallback(() => {
    if (messagesContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = messagesContainerRef.current;
      
      // Safety check for valid measurements
      if (scrollHeight > 0 && clientHeight > 0) {
        // Show button when scrolled up (not at bottom)
        // Use a threshold of 30px to avoid showing the button for minimal scroll differences
        const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
        const isScrolledUp = distanceFromBottom > 30;
        
        console.log('Scroll detected:', { 
          scrollTop, 
          scrollHeight, 
          clientHeight, 
          distanceFromBottom,
          isScrolledUp,
          elementId: messagesContainerRef.current?.id || 'no-id'
        });
        
        setShowScrollButton(isScrolledUp);
      }
    } else {
      console.log('No messages container ref found');
    }
  }, []);

  // Function to scroll to bottom of messages
  const scrollToBottom = useCallback(() => {
    console.log('Scrolling to bottom');
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // Check if scroll button should be shown based on content size
  const checkScrollButtonVisibility = useCallback(() => {
    if (messagesContainerRef.current) {
      const { scrollHeight, clientHeight } = messagesContainerRef.current;
      
      // If content is taller than the container, perform scroll check
      if (scrollHeight > clientHeight) {
        handleScroll();
      }
    }
  }, [handleScroll]);

  // Add scroll event listener when component mounts or messagesContainerRef changes
  useEffect(() => {
    const messagesContainer = messagesContainerRef.current;
    if (messagesContainer) {
      console.log('Adding scroll listener to messages container');
      messagesContainer.addEventListener('scroll', handleScroll);

      // Initial check in case content is already scrolled
      setTimeout(() => {
        checkScrollButtonVisibility();
      }, 500);

      return () => {
        messagesContainer.removeEventListener('scroll', handleScroll);
      };
    }
  }, [handleScroll, checkScrollButtonVisibility, messagesContainerRef.current, currentSession]);

  // Scroll to bottom whenever chat history updates, but check scroll position first
  useEffect(() => {
    // Only do smooth scrolling if we're close to the bottom already
    // or if it's a new message (chatHistory.length increased)
    if (messagesContainerRef.current) {
      const { scrollHeight, scrollTop, clientHeight } = messagesContainerRef.current;
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
      const isAtBottom = distanceFromBottom < 100;
      
      if (isAtBottom) {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      } else if (chatHistory.length <= 2) {
        // For new chats (first few messages), always scroll to bottom
        messagesEndRef.current?.scrollIntoView({ behavior: 'auto' });
      }
      
      // Check if we need to show the scroll button
      // Use multiple timeouts to ensure UI has fully rendered
      [100, 300, 500].forEach(delay => {
        setTimeout(() => {
          checkScrollButtonVisibility();
        }, delay);
      });
    }
  }, [chatHistory, checkScrollButtonVisibility]);

  // When a new session is selected, mark that we need to load docs next time the panel opens
  // and ensure we start at the latest messages
  useEffect(() => {
    hasLoadedDocs.current = false;
    
    // When switching chats, immediately set scroll position to bottom
    if (currentSession && messagesContainerRef.current) {
      // Immediate direct scroll to bottom without animation
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  }, [currentSession]);
  
  // Effect to handle initial rendering and make sure we start at the latest messages
  useEffect(() => {
    // Run once on component mount and whenever chat container is available
    if (messagesContainerRef.current && chatHistory.length > 0) {
      // Direct scrolling to bottom without animation
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  }, []);

  // Ensure the document list is refreshed when:
  // 1. The component mounts and we have a session
  // 2. The files panel is opened 
  // 3. The session changes
  useEffect(() => {
    if (currentSession && isFilesPanelOpen && !hasLoadedDocs.current) {
      loadDocuments();
      hasLoadedDocs.current = true;
    } else if (!isFilesPanelOpen) {
      hasLoadedDocs.current = false;
    }
  }, [isFilesPanelOpen, currentSession, loadDocuments]);

  // Reset scroll position and check scroll button when changing sessions
  useEffect(() => {
    if (currentSession) {
      // Check if we need to show the scroll button
      setTimeout(() => {
        handleScroll();
      }, 500);

      // Check again after a longer delay in case of slow rendering
      setTimeout(() => {
        handleScroll();
      }, 1500);
    }
  }, [currentSession, handleScroll]);

  // Add an effect to check scroll button visibility when chat history changes
  useEffect(() => {
    if (chatHistory.length > 0 && messagesContainerRef.current) {
      // Run the scroll check after a slight delay to let the content render
      setTimeout(() => {
        console.log('Running scroll check after chat history change');
        handleScroll();
      }, 300);
    }
  }, [chatHistory, handleScroll]);

  // Handle document deletion with confirmation
  const handleDeleteDocument = useCallback(async (filename) => {
    // Use the browser's built-in confirm dialog for simplicity
    if (window.confirm(`Are you sure you want to delete ${filename}?`)) {
      // Call the deleteDocument function from the ChatContext
      const success = await deleteDocument(filename);
      
      // Provide visual feedback based on success/failure
      if (success) {
        // Show success toast notification
        toast({
          title: "Document deleted",
          description: `${filename} was successfully removed.`,
          status: "success",
          duration: 3000,
          isClosable: true,
          position: "top",
        });
      } else {
        // Show error toast notification
        toast({
          title: "Deletion failed",
          description: `Could not delete ${filename}. Please try again.`,
          status: "error",
          duration: 5000,
          isClosable: true,
          position: "top",
        });
      }
    }
  }, [deleteDocument, toast]);

  return (
    <Flex flex={1} position="relative" bg="var(--chat-bg)">
      {/* Main Chat Area */}
      <Box 
        flex={1} 
        display="flex" 
        flexDirection="column" 
        h="100vh" 
        bg="var(--chat-bg)" 
        position="relative"
        overflow="hidden"
        marginRight={isFilesPanelOpen ? "300px" : "0"}
        transition="margin-right 0.3s ease-in-out"
      >
        {/* Hidden file input element */}
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          multiple
          accept=".pdf"
          onChange={handleFileChange}
        />
        
        {currentSession ? (
          <>
            {/* Chat Header - Fixed */}
            <Flex 
              justify="space-between" 
              p={2} 
              borderBottom="1px" 
              borderColor="var(--border-color)"
              position="sticky"
              top={0}
              zIndex={10}
              bg="var(--chat-bg)"
            >
              <Text fontWeight="bold" color="var(--foreground)">Chat with AI</Text>
              <HStack spacing={2}>
                {isFilesPanelOpen && (
                  <IconButton
                    icon={<FiChevronLeft />}
                    aria-label="Show files"
                    size="sm"
                    bg="transparent"
                    color="var(--foreground)"
                    _hover={{ bg: "var(--input-bg)" }}
                    onClick={() => toggleFilesPanel(false)}
                    borderRadius="xl"
                  />
                )}
                <IconButton
                  icon={<FiFile />}
                  aria-label="Show files"
                  size="sm"
                  bg={isFilesPanelOpen ? "var(--accent-color)" : "transparent"}
                  color="var(--foreground)"
                  _hover={{ bg: isFilesPanelOpen ? "var(--accent-color)" : "var(--input-bg)" }}
                  onClick={() => toggleFilesPanel()}
                  borderRadius="xl"
                />
                <IconButton
                  icon={<FiTrash2 />}
                  aria-label="Clear chat"
                  size="sm"
                  bg="transparent"
                  color="var(--foreground)"
                  _hover={{ bg: "var(--input-bg)" }}
                  onClick={clearChat}
                  borderRadius="xl"
                />
              </HStack>
            </Flex>

            {/* Empty state with centered input or messages area */}
            {chatHistory.length === 0 ? (
              <Flex 
                flexDirection="column" 
                alignItems="center" 
                justifyContent="center" 
                flex={1}
                px={4}
                overflow="hidden"
                h="calc(100vh - 120px)"
              >
                <Box width="100%" maxW="800px" textAlign="center" mb={8}>
                  <Text color="gray.500" fontSize="lg" mb={8}>
                    Start a new conversation
                  </Text>
                  
                  {/* Show loading animation while uploading files */}
                  {isUploading && (
                    <Box mb={6} p={4} borderRadius="md" bg="var(--input-bg)">
                      <Text mb={2} color="var(--foreground)">Uploading file(s)...</Text>
                      <Progress size="sm" isIndeterminate colorScheme="blue" borderRadius="full" />
                    </Box>
                  )}
                  
                  <form onSubmit={handleSendMessage}>
                    <Box position="relative">
                      <Box
                        bg="var(--input-container-bg)"
                        borderRadius="xl"
                        overflow="hidden"
                        border="1px solid var(--border-color)"
                      >
                        <Flex direction="column" w="100%">
                          <textarea
                            ref={emptyStateInputRef}
                            value={message}
                            onChange={handleMessageInput}
                            onKeyDown={handleKeyDown}
                            placeholder="Type your message..."
                            disabled={loading}
                            style={{
                              width: '100%',
                              border: 'none',
                              outline: 'none',
                              padding: '16px',
                              minHeight: '60px',
                              maxHeight: `${MAX_LINES_HEIGHT}px`,
                              height: 'auto',
                              resize: 'none',
                              background: 'transparent',
                              color: 'var(--input-text)',
                              fontFamily: 'inherit',
                              fontSize: 'inherit',
                              lineHeight: 'inherit',
                              overflow: 'auto',
                              opacity: loading ? 0.6 : 1,
                              cursor: loading ? 'not-allowed' : 'text',
                            }}
                          />
                          
                          <Flex 
                            borderTop="1px solid var(--border-color)" 
                            py={2} 
                            px={3} 
                            justify="space-between" 
                            align="center"
                          >
                            <HStack spacing={2}>
                              <Tooltip label="Upload documents">
                                <IconButton
                                  icon={<Box as="span" fontSize="xl">+</Box>}
                                  aria-label="Upload document"
                                  bg="transparent"
                                  color="var(--foreground)"
                                  _hover={{ bg: "rgba(255,255,255,0.1)" }}
                                  onClick={handleUploadClick}
                                  borderRadius="full"
                                  size="sm"
                                />
                              </Tooltip>
                              <Flex 
                                alignItems="center" 
                                bg="transparent"
                                borderRadius="full"
                                px={2}
                                py={1}
                                h="32px"
                                minW="70px"
                                _hover={{ bg: "rgba(255,255,255,0.1)" }}
                              >
                                <Text fontSize="xs" fontWeight="bold" mr={1} color="var(--foreground)">RAG</Text>
                                <Switch 
                                  isChecked={useRAG} 
                                  onChange={toggleRAG} 
                                  colorScheme="blue"
                                  size="sm"
                                  display="inline-flex"
                                  onClick={(e) => e.stopPropagation()}
                                />
                              </Flex>
                            </HStack>
                            
                            <IconButton
                              type="submit"
                              icon={<Box as="span" fontSize="xl">↑</Box>}
                              aria-label="Send message"
                              bg="var(--button-bg)"
                              color="white"
                              _hover={{ bg: "var(--button-hover)" }}
                              isLoading={loading}
                              disabled={!message.trim() || loading}
                              borderRadius="full"
                              size="sm"
                            />
                          </Flex>
                        </Flex>
                      </Box>
                    </Box>
                  </form>
                </Box>
              </Flex>
            ) : (
              <>
                {/* Messages Area - Scrollable */}
                <Box 
                  ref={messagesContainerRef}
                  id="messages-container"
                  flex={1} 
                  overflow="auto" 
                  display="flex" 
                  flexDirection="column" 
                  alignItems="center"
                  py={4}
                  position="relative"
                  onScroll={handleScroll}
                  css={{
                    '&::-webkit-scrollbar': {
                      width: '8px',
                    },
                    '&::-webkit-scrollbar-track': {
                      background: 'var(--chat-bg)',
                    },
                    '&::-webkit-scrollbar-thumb': {
                      background: '#555',
                      borderRadius: '4px',
                    },
                    '&::-webkit-scrollbar-thumb:hover': {
                      background: '#777',
                    },
                    height: 'calc(100vh - 130px)',
                  }}
                >
                  <Container 
                    maxW="800px" 
                    p={0}
                    h="auto"
                  >
                    <VStack 
                      spacing={4} 
                      align="stretch" 
                      px={2}
                      pb={2}
                      w="100%"
                    >
                      {chatHistory.map((msg, index) => (
                        msg.type === 'human' ? (
                          // Human messages - blue background, right-aligned
                          <Flex key={index} justify="flex-end" width="100%">
                            <Box
                              bg="var(--chat-human-bg)"
                              p="10px 14px 8px 14px"
                              borderRadius="xl"
                              maxWidth="80%"
                              color="var(--foreground)"
                              alignSelf="flex-end"
                            >
                              <MemoizedMarkdown content={msg.content} />
                            </Box>
                          </Flex>
                        ) : (
                          // AI messages - no background, left-aligned
                          <Box 
                            key={index}
                            p={3}
                            color="var(--foreground)"
                            width="100%"
                          >
                            <MemoizedMarkdown content={msg.content} />
                            {msg.document_info && <Sources documentInfo={msg.document_info} />}
                          </Box>
                        )
                      ))}
                      
                      {/* Show loading animation while uploading files */}
                      {isUploading && (
                        <Box mb={4} p={4} borderRadius="md" bg="var(--input-bg)">
                          <Text mb={2} color="var(--foreground)">Uploading file(s)...</Text>
                          <Progress size="sm" isIndeterminate colorScheme="blue" borderRadius="full" />
                        </Box>
                      )}
                      
                      {loading && !isUploading && (
                        <Flex justify="center" py={4}>
                          <Spinner size="md" color="var(--accent-color)" />
                        </Flex>
                      )}
                      <div ref={messagesEndRef} />
                    </VStack>
                  </Container>
                </Box>

                {/* Message Input for non-empty chat - Fixed at bottom */}
                <Box
                  position="sticky"
                  bottom={0}
                  left={0}
                  right={0}
                  py={4}
                  bg="var(--chat-bg)"
                  borderTop="1px"
                  borderColor="var(--border-color)"
                  width="100%"
                  display="flex"
                  justifyContent="center"
                  zIndex={10}
                >
                  {/* Scroll-to-bottom button - Always place in DOM but control visibility with opacity */}
                  <IconButton
                    icon={<FiArrowDown size={20} />}
                    aria-label="Scroll to bottom"
                    position="absolute"
                    top="-24px"
                    left="50%"
                    transform="translateX(-50%)"
                    zIndex={15}
                    bg="var(--button-bg)"
                    color="white"
                    borderRadius="full"
                    boxShadow="0 2px 8px rgba(0, 0, 0, 0.4)"
                    _hover={{ bg: "var(--button-hover)", transform: "translateX(-50%) scale(1.1)" }}
                    onClick={scrollToBottom}
                    size="md"
                    transition="all 0.3s ease"
                    opacity={showScrollButton ? 1 : 0}
                    visibility={showScrollButton ? "visible" : "hidden"}
                    width="40px"
                    height="40px"
                  />
                  
                  <Container maxW="800px" px={4}>
                    <form onSubmit={handleSendMessage}>
                      <Box position="relative">
                        <Box
                          bg="var(--input-container-bg)"
                          borderRadius="xl"
                          overflow="hidden"
                          border="1px solid var(--border-color)"
                        >
                          <Flex direction="column" w="100%">
                            <textarea
                              ref={chatInputRef}
                              value={message}
                              onChange={handleMessageInput}
                              onKeyDown={handleKeyDown}
                              placeholder="Type your message..."
                              disabled={loading}
                              style={{
                                width: '100%',
                                border: 'none',
                                outline: 'none',
                                padding: '16px',
                                minHeight: '60px',
                                maxHeight: `${MAX_LINES_HEIGHT}px`,
                                height: 'auto',
                                resize: 'none',
                                background: 'transparent',
                                color: 'var(--input-text)',
                                fontFamily: 'inherit',
                                fontSize: 'inherit',
                                lineHeight: 'inherit',
                                overflow: 'auto',
                                opacity: loading ? 0.6 : 1,
                                cursor: loading ? 'not-allowed' : 'text',
                              }}
                            />
                            
                            <Flex 
                              borderTop="1px solid var(--border-color)" 
                              py={2} 
                              px={3} 
                              justify="space-between" 
                              align="center"
                            >
                              <HStack spacing={2}>
                                <Tooltip label="Upload documents">
                                  <IconButton
                                    icon={<Box as="span" fontSize="xl">+</Box>}
                                    aria-label="Upload document"
                                    bg="transparent"
                                    color="var(--foreground)"
                                    _hover={{ bg: "rgba(255,255,255,0.1)" }}
                                    onClick={handleUploadClick}
                                    borderRadius="full"
                                    size="sm"
                                  />
                                </Tooltip>
                                <Flex 
                                  alignItems="center" 
                                  bg="transparent"
                                  borderRadius="full"
                                  px={2}
                                  py={1}
                                  h="32px"
                                  minW="70px"
                                  _hover={{ bg: "rgba(255,255,255,0.1)" }}
                                >
                                  <Text fontSize="xs" fontWeight="bold" mr={1} color="var(--foreground)">RAG</Text>
                                  <Switch 
                                    isChecked={useRAG} 
                                    onChange={toggleRAG} 
                                    colorScheme="blue"
                                    size="sm"
                                    display="inline-flex"
                                    onClick={(e) => e.stopPropagation()}
                                  />
                                </Flex>
                              </HStack>
                              
                              <IconButton
                                type="submit"
                                icon={<Box as="span" fontSize="xl">↑</Box>}
                                aria-label="Send message"
                                bg="var(--button-bg)"
                                color="white"
                                _hover={{ bg: "var(--button-hover)" }}
                                isLoading={loading}
                                disabled={!message.trim() || loading}
                                borderRadius="full"
                                size="sm"
                              />
                            </Flex>
                          </Flex>
                        </Box>
                      </Box>
                    </form>
                  </Container>
                </Box>
              </>
            )}
          </>
        ) : (
          <Flex justify="center" align="center" h="100%">
            <Text color="gray.500">
              Select a chat or create a new one to get started
            </Text>
          </Flex>
        )}
      </Box>
      
      {/* Files Panel (right sidebar) */}
      <Box
        position="fixed"
        top={0}
        right={0}
        bottom={0}
        width="300px"
        transform={isFilesPanelOpen ? "translateX(0)" : "translateX(100%)"}
        transition="transform 0.3s ease-in-out"
        zIndex={10}
        bg="var(--sidebar-bg)"
      >
        {isFilesPanelOpen && (
          <FilesPanel 
            files={documents}
            onClose={() => toggleFilesPanel(false)}
            onDeleteDocument={handleDeleteDocument}
          />
        )}
      </Box>
    </Flex>
  );
}