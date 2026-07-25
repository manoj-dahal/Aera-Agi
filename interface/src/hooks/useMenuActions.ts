import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useChatStore, useWorkspaceStore } from '@store/index';
import { system } from '@services/api';

/**
 * Bind the desktop application's native menu to UI actions.
 *
 * aera/desktop/app.py evaluates `window.aeraMenu('<action>')` when a menu item
 * is chosen; this hook installs that handler.
 */
export function useMenuActions() {
  const navigate = useNavigate();

  useEffect(() => {
    window.aeraMenu = (action: string) => {
      if (action.startsWith('view:')) {
        navigate(`/${action.slice(5)}`);
        return;
      }
      switch (action) {
        case 'new-chat':
          useChatStore.getState().newConversation();
          navigate('/dashboard');
          break;
        case 'clear':
          useChatStore.getState().clear();
          break;
        case 'reindex':
          void useWorkspaceStore.getState().reindex();
          break;
        case 'export': {
          const transcript = useChatStore.getState().transcript();
          if (transcript.trim()) {
            void system.saveFile('aera-conversation.md', transcript).catch(() => {});
          }
          break;
        }
        case 'about':
          navigate('/system');
          break;
      }
    };

    window.aeraRefreshAll = () => {
      void useWorkspaceStore.getState().refresh();
    };

    return () => {
      delete window.aeraMenu;
      delete window.aeraRefreshAll;
    };
  }, [navigate]);
}
