export const menuState = () => {
  const menu = $state({
    isOpen: false,
    selectedTab: 'Dashboard', // Default selected tab
  });
  return menu;
};
