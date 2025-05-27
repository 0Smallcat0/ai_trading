"""認證元件（向後相容性模組）

此模組為了保持向後相容性而存在，實際功能已遷移到 ui.auth 子模組。

主要功能：
- 用戶登入和登出
- 兩步驗證支援
- 權限檢查和角色管理
- 會話狀態管理

Example:
    使用認證組件：
    ```python
    from src.ui.components.auth import login_form, check_auth

    if not check_auth():
        login_form()
    else:
        st.write("已登入")
    ```

Note:
    支援服務層認證和簡化認證兩種模式，
    當服務層不可用時會自動降級到簡化模式。
"""

# 為了向後相容性，從新的模組化結構導入所有功能
from ..auth import (
    login_form,
    show_2fa_form,
    check_auth,
    get_user_role,
    logout,
    require_auth,
    USERS,
    SERVICES_AVAILABLE
)

# 保持向後相容性的別名
__all__ = [
    'login_form',
    'show_2fa_form',
    'check_auth',
    'get_user_role',
    'logout',
    'require_auth',
    'USERS',
    'SERVICES_AVAILABLE'
]

# 所有功能已遷移到 ui.auth 子模組，此檔案僅保留向後相容性
