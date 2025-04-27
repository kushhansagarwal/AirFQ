export const menuState = () => {
  const menu = $state({
    isOpen: false,
    selectedTab: 'Demo', // Default selected tab
  });
  return menu;
};
