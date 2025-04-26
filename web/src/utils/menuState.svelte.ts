export const menuState = () => {
  const menu = $state({
    isOpen: false,
    selectedTab: 'Live Map', // Default selected tab
  });
  return menu;
};
