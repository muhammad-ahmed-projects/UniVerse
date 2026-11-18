import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";
import { useAuth } from "@/contexts";
import { ApiError } from "@/services";
import { EyeCloseIcon, EyeIcon } from "@/icons";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router";
import { signInSchema, type SignInFormData } from "./schema";

export default function SignInFormFields() {
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const { login } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignInFormData>({
    resolver: zodResolver(signInSchema),
    defaultValues: {
      username: "",
      password: "",
    },
    mode: "onTouched",
  });

  const handleFormSubmit = async (data: SignInFormData) => {
    setFormError(null);
    try {
      // SignInPage redirects once the auth context has a user.
      await login(data.username, data.password);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Login failed");
    }
  };

  return (
    <form
      onSubmit={handleSubmit(handleFormSubmit)}
      className="space-y-5"
      noValidate
    >
      {formError && (
        <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-500/10 dark:text-red-400">
          {formError}
        </div>
      )}

      <Field data-invalid={Boolean(errors.username)}>
        <FieldLabel className="mb-1.5 block">
          Username <span className="text-red-500">*</span>
        </FieldLabel>
        <Input
          {...register("username")}
          type="text"
          placeholder="Enter your username"
          autoComplete="username"
          aria-invalid={errors.username ? "true" : undefined}
        />
        <FieldError errors={[errors.username]} />
      </Field>

      <Field data-invalid={Boolean(errors.password)}>
        <FieldLabel className="mb-1.5 block">
          Password <span className="text-red-500">*</span>
        </FieldLabel>
        <InputGroup>
          <InputGroupInput
            {...register("password")}
            type={showPassword ? "text" : "password"}
            placeholder="Enter your password"
            autoComplete="current-password"
            aria-invalid={errors.password ? "true" : undefined}
          />
          <InputGroupAddon align="inline-end">
            <InputGroupButton
              size="icon-xs"
              onClick={() => setShowPassword((prev) => !prev)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="text-gray-500 dark:text-gray-400"
            >
              {showPassword ? (
                <EyeIcon className="fill-current" />
              ) : (
                <EyeCloseIcon className="fill-current" />
              )}
            </InputGroupButton>
          </InputGroupAddon>
        </InputGroup>
        <FieldError errors={[errors.password]} />
        <Link
          to="/forgot-password"
          className="mt-1.5 block text-end text-sm text-brand-500 hover:underline"
        >
          Forgot password?
        </Link>
      </Field>

      <div>
        <Button
          className="w-full"
          size="lg"
          type="submit"
          disabled={isSubmitting}
        >
          {isSubmitting ? "Signing In..." : "Sign In"}
        </Button>
      </div>

      <p className="text-center text-sm text-gray-500 dark:text-gray-400">
        New here?{" "}
        <Link to="/signup" className="text-brand-500 hover:underline">
          Create account
        </Link>
      </p>
    </form>
  );
}
