MODULE F2X_ERR

    INTERFACE
        SUBROUTINE F2X_ERR_HANDLE(CODE) BIND(C, name="f2x_err_handle")
            USE, INTRINSIC :: ISO_C_BINDING
            INTEGER, INTENT(IN), VALUE :: CODE
        END SUBROUTINE F2X_ERR_HANDLE
    END INTERFACE

END MODULE F2X_ERR