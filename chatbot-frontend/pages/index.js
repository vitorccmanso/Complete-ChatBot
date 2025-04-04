// Import useEffect hook for side effects like data loading
import { useEffect } from 'react';
// Import UI components from Chakra UI
import { Box, Flex } from '@chakra-ui/react';
// Import custom components
import Sidebar from '../components/Sidebar';
import ChatArea from '../components/ChatArea';
// Import the custom hook to access chat functionality
import { useChat } from '../context/ChatContext';

// Home component is the main page of the application
export default function Home() {
  // Get the loadChatSessions function from our chat context
  const { loadChatSessions } = useChat();

  // Load all chat sessions when the component mounts (page loads)
  useEffect(() => {
    loadChatSessions();
  }, []); // Empty dependency array means this runs once when component mounts

  return (
    // Create a full-screen flex container that's fixed in position
    <Flex h="100vh" overflow="hidden" position="fixed" top={0} left={0} right={0} bottom={0}>
      {/* Sidebar component shows chat history and controls */}
      <Sidebar />
      {/* ChatArea component contains the current conversation */}
      <ChatArea />
    </Flex>
  );
}