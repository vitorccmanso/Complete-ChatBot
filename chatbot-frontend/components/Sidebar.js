// Import React hooks for state management
import { useState, useRef, useCallback } from 'react';
// Import UI components from Chakra UI
import {
  Box,
  VStack,
  Button,
  Text,
  Flex,
  Icon,
  IconButton,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  useDisclosure,
  Portal,
} from '@chakra-ui/react';
// Import icons from react-icons library
import { FiPlus, FiTrash2, FiMoreVertical, FiFile } from 'react-icons/fi';
// Import our custom hook to access chat functionality
import { useChat } from '../context/ChatContext';

// Sidebar component shows chat sessions and new chat button
export default function Sidebar() {
  // Get chat-related functions and state from our context
  const { 
    chatSessions,          // Array of chat session names
    currentSession,        // Currently active session key
    createNewChat,         // Function to create a new chat
    switchChat,            // Function to change to a different chat
    deleteChat,            // Function to delete a chat session
    toggleFilesPanel       // Function to toggle files panel
  } = useChat();
  
  return (
    // Sidebar container with scrolling support
    <Box 
      w="260px" 
      h="100vh" 
      bg="var(--sidebar-bg)" 
      p={4} 
      borderRight="1px" 
      borderColor="var(--border-color)"
      position="sticky"
      top={0}
      left={0}
      overflowY="auto"
      css={{
        // Custom scrollbar styling for better appearance
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
      <VStack spacing={4} align="stretch">
        {/* New Chat button */}
        <Button 
          leftIcon={<FiPlus />} 
          bg="var(--button-bg)"
          color="white"
          _hover={{ bg: "var(--button-hover)" }}
          onClick={createNewChat}
          w="100%"
          borderRadius="xl"
        >
          New Chat
        </Button>

        {/* Chat sessions list */}
        <Box mt={6}>
          <Text fontWeight="bold" mb={2} color="var(--foreground)">Your Chats</Text>
          <VStack spacing={2} align="stretch" maxH="calc(100vh - 200px)" overflowY="auto">
            {chatSessions.map((session) => {
              // Extract session key from filename
              const sessionKey = session.split('.')[0];
              const sessionName = sessionKey;
              // Check if this session is the active one
              const isActive = currentSession === sessionKey;
              
              return (
                // Chat session item with click handler
                <Flex
                  key={sessionKey}
                  p={2}
                  bg={isActive ? "var(--accent-color)" : "transparent"}
                  borderRadius="xl"
                  justify="space-between"
                  align="center"
                  _hover={{ bg: isActive ? "var(--accent-color)" : "var(--input-bg)" }}
                  cursor="pointer"
                  onClick={() => switchChat(sessionKey)}
                >
                  <Text noOfLines={1} color="var(--foreground)">{sessionName}</Text>
                  {/* Menu button */}
                  <Menu placement="bottom-end" closeOnBlur={true}>
                    <MenuButton
                      as={IconButton}
                      icon={<FiMoreVertical />}
                      variant="ghost"
                      aria-label="Chat options"
                      size="sm"
                      color="var(--foreground)"
                      bg="transparent"
                      _hover={{ bg: "rgba(255, 255, 255, 0.1)" }}
                      onClick={(e) => e.stopPropagation()} // Prevent switching chat
                    />
                    <Portal>
                      <MenuList 
                        bg="var(--sidebar-bg)" 
                        borderColor="var(--border-color)"
                        boxShadow="0 4px 6px rgba(0, 0, 0, 0.7)"
                        zIndex={1000}
                        opacity={1}
                      >
                        <MenuItem 
                          icon={<FiFile />}
                          onClick={(e) => {
                            e.stopPropagation(); // Prevent switching chat
                            // Toggle files panel for this chat
                            if (currentSession !== sessionKey) {
                              switchChat(sessionKey);
                              // Give time for the chat to switch, then show files
                              setTimeout(() => toggleFilesPanel(true), 100);
                            } else {
                              toggleFilesPanel(true);
                            }
                          }}
                          bg="var(--sidebar-bg)"
                          color="var(--foreground)"
                          _hover={{ bg: "rgba(255, 255, 255, 0.1)" }}
                        >
                          See Files
                        </MenuItem>
                        <MenuItem 
                          icon={<FiTrash2 />}
                          onClick={(e) => {
                            e.stopPropagation(); // Prevent switching chat
                            deleteChat(sessionKey);
                          }}
                          bg="var(--sidebar-bg)"
                          color="red.400"
                          _hover={{ bg: "rgba(255, 0, 0, 0.1)" }}
                        >
                          Delete Chat
                        </MenuItem>
                      </MenuList>
                    </Portal>
                  </Menu>
                </Flex>
              );
            })}
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
}